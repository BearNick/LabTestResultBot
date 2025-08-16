from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    waiting_for_language = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_file = State()
    # при желании можно добавить:
    # waiting_for_payment = State()
