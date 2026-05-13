import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ValidationError
from django.db.models import F
from django.db.models import Case, When, Value, IntegerField
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import Vehicle, VehicleReservation, VehicleUsage
from .forms import VehicleReservationForm, VehicleUsageCompleteForm, VehicleReservationExtendForm

logger = logging.getLogger(__name__)


def close_orphan_active_usages():
    """Close active usages detached from reservations (usually after admin delete)."""
    now = timezone.now()
    return VehicleUsage.objects.filter(
        reservation__isnull=True,
        dropoff_time__isnull=True,
    ).update(
        dropoff_time=now,
        dropoff_kilometer=F('pickup_kilometer'),
    )


def build_personalized_contract_pdf(reservation: VehicleReservation) -> bytes:
    """Overlay reservation/user fields on top of the contract template PDF."""
    template_path = settings.BASE_DIR / "user_contract" / "Kullanıcı Sözleşmesi.pdf"
    if not template_path.exists():
        raise FileNotFoundError(f"Contract PDF not found: {template_path}")

    full_name = reservation.user.get_full_name() or reservation.user.username
    duty = reservation.user.duty or "-"
    request_date = timezone.localtime(reservation.created_at).strftime("%d.%m.%Y")
    plate = reservation.vehicle.plate
    kilometer = str(reservation.vehicle.initial_kilometer)
    start_local = timezone.localtime(reservation.start_time)
    end_local = timezone.localtime(reservation.end_time)
    start_date = start_local.strftime("%d.%m.%Y")
    start_time = start_local.strftime("%H:%M")
    end_date = end_local.strftime("%d.%m.%Y")
    end_time = end_local.strftime("%H:%M")
    purpose = (reservation.purpose or "-").strip()

    reader = PdfReader(str(template_path))
    writer = PdfWriter()

    # Prefer a Turkish-capable font on Windows.
    font_name = "Helvetica"
    arial_path = Path("C:/Windows/Fonts/arial.ttf")
    times_path = Path("C:/Windows/Fonts/times.ttf")
    if times_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("TimesNewRomanTR", str(times_path)))
            font_name = "TimesNewRomanTR"
        except Exception:
            font_name = "Helvetica"
    elif arial_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("ArialTR", str(arial_path)))
            font_name = "ArialTR"
        except Exception:
            font_name = "Helvetica"

    # ---- Page 1 overlay: plate/km + reservation times + purpose ----
    page1 = reader.pages[0]
    w1 = float(page1.mediabox.width)
    h1 = float(page1.mediabox.height)
    overlay_1_buf = BytesIO()
    c1 = canvas.Canvas(overlay_1_buf, pagesize=(w1, h1))
    c1.setFont(font_name, 13)
    # "... plakalı ve ... kilometrede bulunan aracı ..." satırı
    c1.drawString(70, 705, plate)
    c1.drawString(230, 705, kilometer)
    # ".... tarihinde saat ...'den, .... tarihinde saat ...'e kadar" satırı
    c1.drawString(450, 705, start_date)
    c1.drawString(160, 679, start_time)
    c1.drawString(240, 679, end_date)
    c1.drawString(405, 679, end_time)
    # Kullanım amacı satırı (uzunsa kırp)
    c1.drawString(71, 658, purpose[:90])
    # Kullanıcı bilgileri (tek sayfalı yeni sözleşme için)
    c1.drawString(405, 464, full_name)     # Ad Soyad
    c1.drawString(405, 440, duty)          # Görev
    c1.drawString(405, 392, request_date)  # Talep Tarihi
    c1.save()
    overlay_1_buf.seek(0)
    page1_overlay = PdfReader(overlay_1_buf).pages[0]
    page1.merge_page(page1_overlay)

    # Always output a single-page PDF (first page only).
    writer.add_page(page1)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()


def start_due_reservations():
    """Create usage rows for started reservations that have not been started yet."""
    # Cleanup defensive guard: if a reservation is deleted from admin while usage is active,
    # keep vehicle availability consistent by auto-closing orphan active usages.
    close_orphan_active_usages()

    now = timezone.now()
    due_reservations = VehicleReservation.objects.filter(
        is_active=True,
        start_time__lte=now,
        # Important: user might log in after reservation already ended.
        # We still need a usage row so the mandatory drop-off form can be enforced.
    ).select_related('vehicle', 'user')

    for reservation in due_reservations:
        # Already started for this reservation.
        if VehicleUsage.objects.filter(reservation=reservation).exists():
            continue

        if reservation.vehicle.vehicleusage_set.filter(dropoff_time__isnull=True).exists():
            continue

        last_usage = VehicleUsage.objects.filter(
            vehicle=reservation.vehicle,
            dropoff_time__isnull=False
        ).order_by('-dropoff_time').first()
        pickup_km = (
            last_usage.dropoff_kilometer
            if last_usage and last_usage.dropoff_kilometer is not None
            else reservation.vehicle.initial_kilometer
        )

        try:
            VehicleUsage.objects.create(
                vehicle=reservation.vehicle,
                user=reservation.user,
                pickup_kilometer=pickup_km,
                purpose=reservation.purpose or '',
                reservation=reservation,
            )
        except ValidationError:
            # Expected race/overlap guard: keep request flow healthy, do not raise 500.
            logger.warning(
                "Skipped due reservation start for reservation_id=%s vehicle_id=%s: active usage exists",
                reservation.id,
                reservation.vehicle_id,
            )


def get_pending_usage_for_user(user):
    """Return first ended reservation usage that must be completed by this user."""
    now = timezone.now()
    return VehicleUsage.objects.filter(
        user=user,
        dropoff_time__isnull=True,
        reservation__isnull=False,
        reservation__is_active=True,
        reservation__end_time__lte=now,
    ).select_related('vehicle', 'reservation').order_by('reservation__end_time').first()


def _parse_client_datetime(value: str | None):
    if not value:
        return None
    parsed = parse_datetime(value)
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('vehicle_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Hoş geldiniz, {user.get_full_name()}!')
            next_url = request.GET.get('next', 'vehicle_list')
            return redirect(next_url)
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    
    return render(request, 'vehicles/login.html')


@login_required
def vehicle_list_view(request):
    """Vehicle list view (reservation-focused) grouped by location."""
    start_due_reservations()
    vehicles = Vehicle.objects.filter(is_active=True, show_in_pool=True)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    def build_vehicle_item(vehicle: Vehicle):
        def build_today_busy_spans():
            reservations = vehicle.vehiclereservation_set.filter(
                is_active=True,
                start_time__lt=today_end,
                end_time__gt=today_start,
            ).order_by('start_time')
            raw_spans = []
            for reservation in reservations:
                clipped_start = max(reservation.start_time, today_start)
                clipped_end = min(reservation.end_time, today_end)
                if clipped_end <= clipped_start:
                    continue

                local_start = timezone.localtime(clipped_start)
                local_end = timezone.localtime(clipped_end)
                start_minute = local_start.hour * 60 + local_start.minute
                end_minute = local_end.hour * 60 + local_end.minute
                if end_minute <= start_minute:
                    continue
                raw_spans.append((start_minute, end_minute))

            if not raw_spans:
                return ''

            raw_spans.sort(key=lambda span: span[0])
            merged_spans = [list(raw_spans[0])]
            for start_minute, end_minute in raw_spans[1:]:
                if start_minute <= merged_spans[-1][1]:
                    merged_spans[-1][1] = max(merged_spans[-1][1], end_minute)
                else:
                    merged_spans.append([start_minute, end_minute])
            return ';'.join(f'{start}-{end}' for start, end in merged_spans)

        today_reservations = vehicle.vehiclereservation_set.filter(
            start_time__gte=now,
            start_time__lt=today_end,
            is_active=True,
        ).select_related('user').order_by('start_time')

        nearest_today_reservation = today_reservations.first() if today_reservations.exists() else None
        all_upcoming_reservations = vehicle.get_upcoming_reservations()
        current_usage = vehicle.get_current_usage()
        active_reservation = vehicle.get_active_reservation()
        current_or_upcoming_reservations = vehicle.vehiclereservation_set.filter(
            is_active=True,
            end_time__gte=now,
        )
        is_out_of_service = vehicle.operational_status == 'PASSIVE'
        is_waiting_handover = bool(
            current_usage
            and current_usage.reservation
            and current_usage.reservation.end_time <= now
        )

        return {
            'vehicle': vehicle,
            'current_usage': current_usage,
            'active_reservation': active_reservation,
            'is_waiting_handover': is_waiting_handover,
            'is_out_of_service': is_out_of_service,
            'nearest_today_reservation': nearest_today_reservation,
            'upcoming_reservation_count': all_upcoming_reservations.count(),
            'show_view_reservations': current_or_upcoming_reservations.exists(),
            'today_busy_spans': build_today_busy_spans(),
        }

    atasehir_vehicle_data = [
        build_vehicle_item(v)
        for v in vehicles.filter(location='Ataşehir').order_by('operational_status', 'plate')
    ]
    dilovasi_vehicle_data = [
        build_vehicle_item(v)
        for v in vehicles.filter(location='Dilovası').order_by('operational_status', 'plate')
    ]
    tuzla_vehicle_data = [
        build_vehicle_item(v)
        for v in vehicles.filter(location='Tuzla').order_by('operational_status', 'plate')
    ]
    santis_plaza_vehicle_data = [
        build_vehicle_item(v)
        for v in vehicles.filter(location='Santis Plaza').order_by('operational_status', 'plate')
    ]

    context = {
        'atasehir_vehicle_data': atasehir_vehicle_data,
        'dilovasi_vehicle_data': dilovasi_vehicle_data,
        'tuzla_vehicle_data': tuzla_vehicle_data,
        'santis_plaza_vehicle_data': santis_plaza_vehicle_data,
    }

    return render(request, 'vehicles/vehicle_list.html', context)


@login_required
def vehicle_reservation_create_view(request, vehicle_id):
    """Create a vehicle reservation"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, is_active=True)
    if vehicle.operational_status == 'PASSIVE':
        messages.error(request, 'Araç şu anda kullanım dışıdır. Rezervasyon yapılamaz.')
        return redirect('vehicle_list')
    start_due_reservations()
    if request.method == 'POST':
        form = VehicleReservationForm(request.POST, vehicle=vehicle, user=request.user)
        if form.is_valid():
            try:
                reservation = form.save()
                # Force user to be the logged-in user (security)
                reservation.user = request.user
                reservation.save()
            except ValidationError as exc:
                form.add_error(None, exc)
                message_text = 'Rezervasyon oluşturulamadı. Lütfen uyarıları kontrol edin.'
                if hasattr(exc, 'message_dict') and exc.message_dict:
                    first_key = next(iter(exc.message_dict))
                    if exc.message_dict.get(first_key):
                        message_text = str(exc.message_dict[first_key][0])
                elif hasattr(exc, 'messages') and exc.messages:
                    message_text = str(exc.messages[0])
                messages.error(request, message_text)
            else:
                messages.success(request, f'{vehicle.plate} plakalı araç için rezervasyon oluşturuldu.')
                return redirect('vehicle_reservation_contract_complete', reservation_id=reservation.id)
    else:
        form = VehicleReservationForm(vehicle=vehicle, user=request.user)
    
    return render(request, 'vehicles/vehicle_reservation_create.html', {
        'form': form,
        'vehicle': vehicle
    })


@login_required
def reservation_availability_check_view(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, is_active=True)
    start_time_raw = request.GET.get('start_time')
    end_time_raw = request.GET.get('end_time')

    start_time = _parse_client_datetime(start_time_raw)
    end_time = _parse_client_datetime(end_time_raw)
    if not start_time or not end_time:
        return JsonResponse({'available': False, 'message': 'Başlangıç ve bitiş zamanı gerekli.'}, status=400)

    if end_time <= start_time:
        return JsonResponse({'available': False, 'message': 'Bitiş zamanı başlangıçtan sonra olmalıdır.'})

    if vehicle.operational_status == 'PASSIVE':
        return JsonResponse({'available': False, 'message': 'Araç kullanım dışı olduğu için rezervasyon yapılamaz.'})

    overlap_exists = VehicleReservation.objects.filter(
        vehicle=vehicle,
        is_active=True,
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).exists()
    if overlap_exists:
        return JsonResponse(
            {
                'available': False,
                'message': 'Seçtiğiniz tarih aralığında aracın rezervasyonu vardır.',
            }
        )

    user_overlap_exists = VehicleReservation.objects.filter(
        user=request.user,
        is_active=True,
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).exists()
    if user_overlap_exists:
        return JsonResponse({'available': False, 'message': 'Aynı zaman aralığında başka randevunuz var.'})

    active_usage = VehicleUsage.objects.filter(vehicle=vehicle, dropoff_time__isnull=True).select_related('reservation').first()
    if active_usage:
        usage_reservation_end = active_usage.reservation.end_time if active_usage.reservation else None
        if usage_reservation_end and start_time < usage_reservation_end:
            return JsonResponse(
                {
                    'available': False,
                    'message': f'Araç şu an kullanımda. En erken {usage_reservation_end:%d.%m.%Y %H:%M} sonrası seçebilirsiniz.',
                }
            )
        if start_time <= timezone.now():
            return JsonResponse({'available': False, 'message': 'Araç şu an kullanımda. Daha ileri bir saat seçin.'})

    return JsonResponse({'available': True, 'message': 'Araç seçilen zaman aralığında uygun görünüyor.'})


@login_required
def vehicle_reservation_contract_complete_view(request, reservation_id):
    """Show post-reservation screen with auto download + countdown redirect."""
    reservation = get_object_or_404(
        VehicleReservation.objects.select_related('user', 'vehicle'),
        id=reservation_id,
        user=request.user,
        is_active=True,
    )
    return render(request, 'vehicles/vehicle_reservation_contract_complete.html', {
        'reservation': reservation,
    })


@login_required
def vehicle_reservation_contract_download_view(request, reservation_id):
    """Download personalized user contract PDF after successful reservation."""
    reservation = get_object_or_404(
        VehicleReservation.objects.select_related('user', 'vehicle'),
        id=reservation_id,
        user=request.user,
    )
    try:
        pdf_bytes = build_personalized_contract_pdf(reservation)
    except FileNotFoundError as exc:
        raise Http404(str(exc)) from exc

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Kullanici-Sozlesmesi-{reservation.id}.pdf"
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
    return response


@login_required
def vehicle_usage_complete_view(request):
    """Force user to complete ended reservation usage details."""
    start_due_reservations()
    usage = get_pending_usage_for_user(request.user)
    if usage is None:
        messages.info(request, 'Tamamlanması gereken aktif kullanımınız bulunmuyor.')
        return redirect('vehicle_list')

    if request.method == 'POST':
        form = VehicleUsageCompleteForm(request.POST, instance=usage)
        if form.is_valid():
            completed_usage = form.save(commit=False)
            completed_usage.dropoff_time = timezone.now()
            completed_usage.save()
            # Keep vehicle's visible kilometer in sync with latest drop-off.
            completed_usage.vehicle.initial_kilometer = completed_usage.dropoff_kilometer
            completed_usage.vehicle.save(update_fields=['initial_kilometer'])
            messages.success(request, 'Araç kullanım formu kaydedildi.')
            return redirect('vehicle_list')
    else:
        form = VehicleUsageCompleteForm(instance=usage)

    return render(request, 'vehicles/vehicle_usage_complete.html', {
        'form': form,
        'usage': usage,
    })


@login_required
def pending_usage_status_view(request):
    """Lightweight endpoint for client polling and immediate redirect."""
    start_due_reservations()
    pending = get_pending_usage_for_user(request.user)
    return JsonResponse({
        'has_pending_usage': bool(pending),
        'redirect_url': '/cartrack/vehicle/usage/complete/' if pending else '',
    })


@login_required
def vehicle_kilometer_status_view(request):
    """Return latest visible vehicle kilometers for home card auto-refresh."""
    vehicles = Vehicle.objects.filter(is_active=True, show_in_pool=True).values('id', 'initial_kilometer')
    return JsonResponse({
        'vehicles': {str(item['id']): item['initial_kilometer'] for item in vehicles}
    })


@login_required
def vehicle_reservation_list_view(request, vehicle_id):
    """List reservations for a vehicle"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, is_active=True)
    now = timezone.now()
    reservations = VehicleReservation.objects.filter(
        vehicle=vehicle,
        user=request.user,
        is_active=True
    ).annotate(
        sort_group=Case(
            When(end_time__lt=now, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).select_related('user').order_by('sort_group', '-start_time', '-end_time', '-id')
    
    return render(request, 'vehicles/vehicle_reservation_list.html', {
        'vehicle': vehicle,
        'reservations': reservations
    })


@login_required
def vehicle_reservation_cancel_view(request, reservation_id):
    """Cancel a reservation"""
    reservation = get_object_or_404(
        VehicleReservation,
        id=reservation_id,
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        reservation.is_active = False
        reservation.save()
        messages.success(request, 'Rezervasyon iptal edildi.')
        return redirect('vehicle_list')
    
    return render(request, 'vehicles/vehicle_reservation_cancel.html', {
        'reservation': reservation
    })


@login_required
def vehicle_reservation_finish_view(request, reservation_id):
    """Finish current reservation early and force handover form."""
    reservation = get_object_or_404(
        VehicleReservation.objects.select_related('vehicle'),
        id=reservation_id,
        user=request.user,
        is_active=True,
    )
    start_due_reservations()

    if not reservation.is_current():
        messages.error(request, 'Sadece aktif rezervasyon bitirilebilir.')
        return redirect('vehicle_reservation_list', vehicle_id=reservation.vehicle_id)

    if request.method == 'POST':
        now = timezone.now()
        if reservation.end_time > now:
            VehicleReservation.objects.filter(pk=reservation.pk).update(end_time=now)

        messages.info(request, 'Rezervasyon bitirildi. Devam etmek için teslim formunu doldurun.')
        return redirect('vehicle_usage_complete')

    return redirect('vehicle_reservation_list', vehicle_id=reservation.vehicle_id)


@login_required
def vehicle_reservation_extend_view(request, reservation_id):
    """Allow reservation owner to create a direct extension reservation."""
    reservation = get_object_or_404(
        VehicleReservation.objects.select_related('vehicle'),
        id=reservation_id,
        user=request.user,
        is_active=True,
    )

    if reservation.end_time <= timezone.now():
        messages.error(request, 'Süresi bitmiş rezervasyon uzatılamaz.')
        return redirect('vehicle_reservation_list', vehicle_id=reservation.vehicle_id)

    if request.method == 'POST':
        form = VehicleReservationExtendForm(request.POST, base_end_time=reservation.end_time)
        if form.is_valid():
            new_reservation = VehicleReservation(
                vehicle=reservation.vehicle,
                user=request.user,
                start_time=reservation.end_time,
                end_time=form.cleaned_data['new_end_time'],
                purpose=reservation.purpose,
                is_active=True,
            )
            try:
                new_reservation.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f'Rezervasyon {reservation.end_time:%d.%m.%Y %H:%M} başlangıcı ile uzatıldı.'
                )
                return redirect('vehicle_reservation_list', vehicle_id=reservation.vehicle_id)
    else:
        form = VehicleReservationExtendForm(base_end_time=reservation.end_time)

    return render(request, 'vehicles/vehicle_reservation_extend.html', {
        'reservation': reservation,
        'form': form,
    })

