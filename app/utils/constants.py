from enum import Enum

class SettingKeys(Enum):
    CHARACTER_ARC_GENERATION_MODEL = "character_arc_generation_model"
    CHARACTER_ARC_GENERATION_TEMPERATURE = "character_arc_generation_temperature"
    PLOT_BEAT_GENERATION_MODEL = "plot_beat_generation_model"
    PLOT_BEAT_GENERATION_TEMPERATURE = "plot_beat_generation_temperature"
    PLOT_SUMMARY_GENERATION_MODEL = "plot_summary_generation_model"
    PLOT_SUMMARY_GENERATION_TEMPERATURE = "plot_summary_generation_temperature"