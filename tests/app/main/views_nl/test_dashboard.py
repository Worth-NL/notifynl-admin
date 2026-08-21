from app.main.views_nl.dashboard import aggregate_notifications_stats, get_annual_usage_breakdown


def test_aggregate_notifications_stats_includes_messagebox():
    template_statistics = [
        {"template_type": "messagebox", "status": "delivered", "count": 3},
        {"template_type": "messagebox", "status": "permanent-failure", "count": 1},
        {"template_type": "sms", "status": "delivered", "count": 2},
    ]

    result = aggregate_notifications_stats(template_statistics)

    assert set(result.keys()) == {"sms", "email", "letter", "messagebox"}
    assert result["messagebox"] == {"requested": 4, "delivered": 3, "failed": 1}


def test_aggregate_notifications_stats_messagebox_defaults_to_zero_when_no_stats():
    result = aggregate_notifications_stats([{"template_type": "email", "status": "delivered", "count": 1}])

    assert result["messagebox"] == {"requested": 0, "delivered": 0, "failed": 0}


def test_get_annual_usage_breakdown_includes_messagebox_count_only():
    usage = [
        {"notification_type": "messagebox", "notifications_sent": 5, "cost": 0, "chargeable_units": 0},
        {"notification_type": "messagebox", "notifications_sent": 2, "cost": 0, "chargeable_units": 0},
        {"notification_type": "email", "notifications_sent": 10, "cost": 0, "chargeable_units": 0},
    ]

    result = get_annual_usage_breakdown(usage, free_sms_fragment_limit=0)

    assert result["messageboxes_sent"] == 7
    assert "messagebox_cost" not in result
    assert "messagebox_breakdown" not in result
