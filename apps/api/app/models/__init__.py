from app.models.benchmark import HANDICAP_BUCKETS, StrokesGainedBenchmark
from app.models.course import Course, Hole
from app.models.garmin_connection import GarminConnection
from app.models.practice import PracticeSession, PracticeShot
from app.models.round import Round, RoundStatus
from app.models.shot import Lie, Shot
from app.models.user import User
from app.models.virtual_round import SimPlatform, VirtualRound

__all__ = [
    "Course",
    "GarminConnection",
    "HANDICAP_BUCKETS",
    "Hole",
    "PracticeSession",
    "PracticeShot",
    "Round",
    "RoundStatus",
    "Lie",
    "Shot",
    "SimPlatform",
    "StrokesGainedBenchmark",
    "User",
    "VirtualRound",
]
