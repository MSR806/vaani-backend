from app.services.story_generator_service.character_arc_generator import CharacterArcGenerator
from app.services.story_generator_service.plot_generator import PlotBeatGenerator
from app.database import get_db



async def start_generation(story_board_id: int):
    db = get_db()
    story_board_inst = CharacterArcGenerator(db, story_board_id)
    await story_board_inst.execute()

    plot_beat_inst = PlotBeatGenerator(db, story_board_id)
    await plot_beat_inst.execute()