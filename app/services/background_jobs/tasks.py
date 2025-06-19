import logging

from app.database import get_db
from app.services.background_jobs import enqueue_job
from app.services.storyboard.character_arc_generator import CharacterArcGenerator
from app.services.storyboard.plot_generator import PlotBeatGenerator
from app.services.template_generator.template_manager import TemplateManager

logger = logging.getLogger(__name__)


async def create_template_task(book_id: int, template_id: int):
    db = next(get_db())
    manager = TemplateManager(book_id, db)
    await manager.run(template_id)


def add_template_creation_task_to_bg_jobs(book_id: int, template_id: int):
    enqueue_job(create_template_task, book_id=book_id, template_id=template_id)


async def generate_character_arcs_task(storyboard_id: int):
    db = next(get_db())
    storyboard_inst = CharacterArcGenerator(db, storyboard_id)
    await storyboard_inst.execute()


def add_generate_character_arcs_task_to_bg_jobs(storyboard_id: int):
    enqueue_job(generate_character_arcs_task, storyboard_id=storyboard_id)


async def generate_plot_beats_task(storyboard_id: int):
    db = next(get_db())
    storyboard_inst = PlotBeatGenerator(db, storyboard_id)
    await storyboard_inst.execute()


def add_generate_plot_beats_task_to_bg_jobs(storyboard_id: int):
    enqueue_job(generate_plot_beats_task, storyboard_id=storyboard_id)
