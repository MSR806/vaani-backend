from enum import Enum


class SettingKeys(Enum):
    # Existing settings
    CHARACTER_ARC_GENERATION_MODEL = "character_arc_generation_model"
    CHARACTER_ARC_GENERATION_TEMPERATURE = "character_arc_generation_temperature"

    PLOT_BEAT_GENERATION_MODEL = "plot_beat_generation_model"
    PLOT_BEAT_GENERATION_TEMPERATURE = "plot_beat_generation_temperature"

    PLOT_SUMMARY_GENERATION_MODEL = "plot_summary_generation_model"
    PLOT_SUMMARY_GENERATION_TEMPERATURE = "plot_summary_generation_temperature"

    CHAPTER_SUMMARY_GENERATION_FROM_STORYBOARD_MODEL = (
        "chapter_summary_generation_from_storyboard_model"
    )
    CHAPTER_SUMMARY_GENERATION_FROM_STORYBOARD_TEMPERATURE = (
        "chapter_summary_generation_from_storyboard_temperature"
    )

    CHAPTER_SUMMARY_GENERATION_FOR_TEMPLATE_MODEL = "chapter_summary_generation_for_template_model"
    CHAPTER_SUMMARY_GENERATION_FOR_TEMPLATE_TEMPERATURE = (
        "chapter_summary_generation_for_template_temperature"
    )

    EXTRACTING_CHARACTER_ARCS_MODEL = "extracting_character_arcs_model"
    EXTRACTING_CHARACTER_ARCS_TEMPERATURE = "extracting_character_arcs_temperature"

    EXTRACTING_PLOT_BEATS_MODEL = "extracting_plot_beats_model"
    EXTRACTING_PLOT_BEATS_TEMPERATURE = "extracting_plot_beats_temperature"

    CHARACTER_ARC_TEMPLATE_MODEL = "character_arc_template_model"
    CHARACTER_ARC_TEMPLATE_TEMPERATURE = "character_arc_template_temperature"

    PLOT_BEATS_TEMPLATE_MODEL = "plot_beats_template_model"
    PLOT_BEATS_TEMPLATE_TEMPERATURE = "plot_beats_template_temperature"

    # Character identification settings
    CHARACTER_IDENTIFICATION_MODEL = "character_identification_model"
    CHARACTER_IDENTIFICATION_TEMPERATURE = "character_identification_temperature"
