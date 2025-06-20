import logging
from typing import Tuple

from sqlalchemy.orm import Session

from app.services.setting_service import get_setting_by_key
from app.utils.constants import SettingKeys

logger = logging.getLogger(__name__)


class ModelSettings:
    def __init__(self, db: Session):
        self.db = db

    def get_model_and_temperature(
        self,
        setting_key_pair: Tuple[str, str],
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.5,
    ) -> Tuple[str, float]:
        model_key, temp_key = setting_key_pair

        try:
            model = get_setting_by_key(self.db, model_key).value
        except Exception as e:
            logger.warning(f"Could not get model setting {model_key}, using default: {str(e)}")
            model = default_model

        try:
            temp_value = get_setting_by_key(self.db, temp_key).value
            temperature = float(temp_value)
        except Exception as e:
            logger.warning(f"Could not get temperature setting {temp_key}, using default: {str(e)}")
            temperature = default_temperature

        return model, temperature

    # Storyboard generation methods
    def character_arc_generation(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.CHARACTER_ARC_GENERATION_MODEL.value,
                SettingKeys.CHARACTER_ARC_GENERATION_TEMPERATURE.value,
            )
        )

    def plot_beat_generation(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.PLOT_BEAT_GENERATION_MODEL.value,
                SettingKeys.PLOT_BEAT_GENERATION_TEMPERATURE.value,
            )
        )

    def plot_summary_generation(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.PLOT_SUMMARY_GENERATION_MODEL.value,
                SettingKeys.PLOT_SUMMARY_GENERATION_TEMPERATURE.value,
            )
        )

    # Chapter summary methods
    def chapter_summary_from_storyboard(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.CHAPTER_SUMMARY_GENERATION_FROM_STORYBOARD_MODEL.value,
                SettingKeys.CHAPTER_SUMMARY_GENERATION_FROM_STORYBOARD_TEMPERATURE.value,
            )
        )

    def chapter_summary_for_template(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.CHAPTER_SUMMARY_GENERATION_FOR_TEMPLATE_MODEL.value,
                SettingKeys.CHAPTER_SUMMARY_GENERATION_FOR_TEMPLATE_TEMPERATURE.value,
            )
        )

    # Template generation methods
    def extracting_character_arcs(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.EXTRACTING_CHARACTER_ARCS_MODEL.value,
                SettingKeys.EXTRACTING_CHARACTER_ARCS_TEMPERATURE.value,
            )
        )

    def extracting_plot_beats(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.EXTRACTING_PLOT_BEATS_MODEL.value,
                SettingKeys.EXTRACTING_PLOT_BEATS_TEMPERATURE.value,
            )
        )

    def character_arc_template(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.CHARACTER_ARC_TEMPLATE_MODEL.value,
                SettingKeys.CHARACTER_ARC_TEMPLATE_TEMPERATURE.value,
            )
        )

    def plot_beats_template(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.PLOT_BEATS_TEMPLATE_MODEL.value,
                SettingKeys.PLOT_BEATS_TEMPLATE_TEMPERATURE.value,
            )
        )

    def character_identification(self) -> Tuple[str, float]:
        return self.get_model_and_temperature(
            (
                SettingKeys.CHARACTER_IDENTIFICATION_MODEL.value,
                SettingKeys.CHARACTER_IDENTIFICATION_TEMPERATURE.value,
            )
        )
