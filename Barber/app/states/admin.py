from aiogram.fsm.state import State, StatesGroup


class AdminFSM(StatesGroup):
    choosing_action = State()
    picking_date = State()
    entering_time = State()
    confirming_cancel = State()

