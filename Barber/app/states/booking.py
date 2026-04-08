from aiogram.fsm.state import State, StatesGroup


class BookingFSM(StatesGroup):
    picking_date = State()
    picking_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()

