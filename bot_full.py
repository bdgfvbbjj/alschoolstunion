from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = "8456230167:AAHCaeyIsgjBRaBvZ_4Q29awaUv4Ikd3rzw"
ADMIN_ID = 123456789

bot = Bot(API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

registered_ips = set()  # Проверка IP

# Состояния регистрации
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_class = State()
    waiting_for_selfie = State()
    waiting_for_image_choice = State()
    waiting_for_confirmation = State()

# Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add("Начать регистрацию")

cancel_button = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_button.add("Отмена")

# Старт и открытие Web App
@dp.message_handler(lambda message: message.text == "Начать регистрацию")
async def start_registration(message: types.Message):
    web_app = WebAppInfo(url="https://ваш_сайт_с_webapp.com")  # URL вашего веб-приложения
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(text="Открыть регистрацию", web_app=web_app))
    await message.answer("Откройте веб-страницу для продолжения регистрации:", reply_markup=markup)

# Получаем IP из WebApp
@dp.message_handler(content_types=types.ContentType.TEXT)
async def receive_ip(message: types.Message, state: FSMContext):
    user_ip = message.text
    if user_ip in registered_ips:
        await message.answer("❌ Регистрация с этого IP уже была.")
        return
    registered_ips.add(user_ip)
    await message.answer("IP проверен. Введите ваше имя:", reply_markup=cancel_button)
    await Registration.waiting_for_name.set()

@dp.message_handler(lambda message: message.text == "Отмена", state='*')
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено.", reply_markup=main_menu)

@dp.message_handler(state=Registration.waiting_for_name)
async def name_received(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ваш класс:", reply_markup=cancel_button)
    await Registration.waiting_for_class.set()

@dp.message_handler(state=Registration.waiting_for_class)
async def class_received(message: types.Message, state: FSMContext):
    await state.update_data(student_class=message.text)
    await message.answer("Отправьте ваше селфи:", reply_markup=cancel_button)
    await Registration.waiting_for_selfie.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Registration.waiting_for_selfie)
async def selfie_received(message: types.Message, state: FSMContext):
    await state.update_data(selfie=message.photo[-1].file_id)

    # Две картинки для выбора
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Картинка 1", callback_data="image_1"),
        InlineKeyboardButton("Картинка 2", callback_data="image_2")
    )
    await message.answer("Выберите одно из изображений:", reply_markup=markup)
    await Registration.waiting_for_image_choice.set()

@dp.callback_query_handler(lambda c: c.data.startswith('image_'), state=Registration.waiting_for_image_choice)
async def image_choice(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(chosen_image=callback_query.data)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Да", callback_data="confirm_yes"),
        InlineKeyboardButton("Нет", callback_data="confirm_no")
    )
    await bot.send_message(callback_query.from_user.id, "Вы точно хотите выбрать это изображение?", reply_markup=markup)
    await Registration.waiting_for_confirmation.set()

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_'), state=Registration.waiting_for_confirmation)
async def confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "confirm_yes":
        data = await state.get_data()
        await bot.send_message(ADMIN_ID,
                               f"Новый студент зарегистрирован:\n"
                               f"Имя: {data['name']}\n"
                               f"Класс: {data['student_class']}\n"
                               f"Выбранное изображение: {data['chosen_image']}")
        await bot.send_photo(ADMIN_ID, data['selfie'], caption="Селфи студента")
        await bot.send_message(callback_query.from_user.id, "✅ Регистрация завершена!", reply_markup=main_menu)
        await state.finish()
    else:
        await bot.send_message(callback_query.from_user.id, "Выбор отменен. Регистрация прервана.", reply_markup=main_menu)
        await state.finish()

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
