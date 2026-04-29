from .auth import (
    signup, user_logout, password_reset_request, set_new_password, login_view,
)
from .driver import (
    home, enter_head_count, success, submission_history,
    get_driver_name, staff_id_autocomplete, duty_card_no_autocomplete,
    route_autocomplete, shift_time_autocomplete, get_duty_card_details,
)
from .reports import (
    report_view, download_report, admin_dashboard, dashboard_data,
    duty_card_submission_data, add_reports, add_delay_report,
    ekg_breakdown, subcategory_selection,
)
from .stm import (
    stm_dashboard, fleet_counts_api, download_fleet_report,
    ajax_search_route, route_details, stm_timetables,
    public_stm_dashboard, get_most_delayed_trips_api,
    get_otp_chart_data, filter_dashboard,
    get_top_delayed_load_trips_api, get_daily_delay_details, get_otp_details,
)
from .upload import (
    upload_view, download_file, upload_gpsreports, upload_salik, upload_mileage,
)
from .bus import (
    submit_bus_km, duty_card_suggestions, bus_no_suggestions,
    bus_trip_details, ekstm_47seater_report_dashboard,
)
from .profile import user_profile, oauth2callback, drive_image_proxy
