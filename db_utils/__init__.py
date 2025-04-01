# Database utilities module
from .db_manager import (
    initialize_db,
    save_transcription,
    get_transcription,
    get_latest_transcriptions,
    get_transcriptions_by_date_range,
    close_all_connections,
    save_optimized_transcription,
    get_latest_optimized_transcriptions,
    get_optimized_transcriptions_by_date
)
