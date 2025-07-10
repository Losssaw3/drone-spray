policies = (
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

def check_operation(id, details) -> bool:
    """ Проверка возможности совершения обращения. """
    src: str = details.get("source")
    dst: str = details.get("deliver_to")
    opr: str = details.get("operation")

    if not all((src, dst, opr)):
        return False

    print(f"[info] checking policies for event {id},  {src}->{dst}: {opr}")

    return {"src": src, "dst": dst, "opr": opr} in policies