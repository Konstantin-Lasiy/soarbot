import run_screen as SS
from configs import config

SS.send_to_telegram('Test run successfully!', config.test_chat_id)