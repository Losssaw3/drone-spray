import pytest


def check_operation(id, details,polices) -> bool:
    """ Проверка возможности совершения обращения. """
    src: str = details.get("source")
    dst: str = details.get("deliver_to")
    opr: str = details.get("operation")

    if not all((src, dst, opr)):
        return False
    return {"src": src, "dst": dst, "opr": opr} in polices

@pytest.fixture
def polices():
    return (
    {"src": "barometer", "dst": "limiter", "opr": "current_height"},    
    {"src": "barometer", "dst": "drone-status-control", "opr": "current_height"},

    {"src": "camera", "dst": "mission-control", "opr": "photo"},

    {"src": "communication", "dst": "encryption", "opr": "turn_on"},
    {"src": "communication", "dst": "encryption", "opr": "confirm_photo"},

    {"src": "complex", "dst": "limiter", "opr": "current_coords"},
    {"src": "complex", "dst": "drone-status-control", "opr": "current_coords"},

    {"src": "drone-status-control", "dst": "message-sending", "opr": "status"},
    {"src": "drone-status-control", "dst": "message-sending", "opr": "flight-report"},
    {"src": "drone-status-control", "dst": "mission-control", "opr": "current_coords"},

    {"src": "encryption", "dst": "drone-status-control", "opr": "turn_on"},
    {"src": "encryption", "dst": "limiter", "opr": "set_mission"},
    {"src": "encryption", "dst": "task-orchestrator", "opr": "set_mission"},
    {"src": "encryption", "dst": "mission-control", "opr": "set_mission"},
    {"src": "encryption", "dst": "mission-control", "opr": "confirm_photo"},
    {"src": "encryption", "dst": "communication", "opr": "status"},
    {"src": "encryption", "dst": "communication", "opr":  "photo"},
    {"src": "encryption", "dst": "communication", "opr": "flight-report"},
    
    

    {"src": "gps", "dst": "complex", "opr": "current_coords_gps"},

    {"src": "internal", "dst": "complex", "opr": "current_coords_ins"},

    {"src": "limiter", "dst": "servo", "opr": "move"},
    {"src": "limiter", "dst": "servo", "opr": "pause"},

    {"src": "message-sending", "dst": "encryption", "opr": "status"},
    {"src": "message-sending", "dst": "encryption", "opr": "photo"},
    {"src": "message-sending", "dst": "encryption", "opr": "flight-report"},

    {"src": "mission-control", "dst": "limiter", "opr": "resume"},
    {"src": "mission-control", "dst": "limiter", "opr": "pause"},
    {"src": "mission-control", "dst": "camera", "opr": "take_photo"},
    {"src": "mission-control", "dst": "sprayer-control", "opr": "turn_off"},
    {"src": "mission-control", "dst": "sprayer-control", "opr": "turn_on"},
    {"src": "mission-control", "dst": "message-sending", "opr": "photo"},

    {"src": "movement-calculation", "dst": "limiter", "opr": "set_routes"},

    {"src": "sprayer-control", "dst": "sprayer", "opr": "turn_off"},
    {"src": "sprayer-control", "dst": "sprayer", "opr": "turn_on"},

    {"src": "task-orchestrator", "dst": "movement-calculation", "opr": "set_mission"},
)


@pytest.mark.parametrize("details, expected", [
    ({"source": "barometer", "deliver_to": "limiter", "operation": "current_height"}, True),
    ({"source": "camera", "deliver_to": "mission-control", "operation": "photo"}, True),
    ({"source": "gps", "deliver_to": "complex", "operation": "current_coords_gps"}, True),
])
def test_allowed_operations(details, expected, polices):
    assert check_operation("test_id", details, polices) == expected


@pytest.mark.parametrize("details, expected", [
    ({"source": "barometer", "deliver_to": "limiter", "operation": "invalid_op"}, False),
    ({"source": "invalid_src", "deliver_to": "complex", "operation": "current_coords_gps"}, False),
    ({"source": "gps", "deliver_to": "invalid_dst", "operation": "current_coords_gps"}, False),
])
def test_denied_operations(details, expected, polices):
    assert check_operation("test_id", details, polices) == expected


@pytest.mark.parametrize("details", [
    {"source": "barometer", "deliver_to": "limiter"},  
    {"source": "barometer", "operation": "current_height"},
    {"deliver_to": "limiter", "operation": "current_height"},
    {},
])
def test_incomplete_details(details, polices):
    assert check_operation("test_id", details, polices) is False