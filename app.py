import os
import sys
import datetime
import logging
import json
import time
import threading
import requests
# lo uso para convertir una cadena de estaciones (de la API) en diccionario
import ast
import schedule

import telebot
from telebot.types import ForceReply
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
import schedule

# Para crear nuestro servidor web propio LOCAL
from flask import Flask, request
from waitress import serve

from App.modulos import sst_server
from App.modulos.utils import *
from flask import Flask

__version__ = "V 1 0"
__date__ = "2023/12/12"
__author__ = "Cubiella, Alvaro"

global estaciones, estacion_seleccionada
global user_id_admin

estaciones = {}
estacion_seleccionada = None
user_admin = ()

user_id_admin = (
    5421431478,
)
user_admin = (
    'AlvaroCubiella',
)

w_list = (
    'AlvaroCubiella',
    'EmmanuelZel',
    'NoeManik4',
    'Raul_Reta',
    'Jorge_fabrego',
    'Harold_Fenco',
    'gnmolinari',
)

# Lista de comandos para usuarios
w_cmd_lit = (
    'start',
    'info',
    'help',
)

# Establezco a partir de que nivel se imprimen los mensajes y formato
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s -  %(processName)s - %(levelname)s - %(message)s",
                    filename='Telegram_BOT.log',
                    filemode='a')

file = f"{os.getcwd()}{os.sep}T_Bot.json"

try:
    with open(file, 'r') as f:
        cfg = json.load(f)
except:
    logging.critical(f"No se pudo cargar el archivo de configuracion {file}")
    sys.exit(0)

# Estacion
estacion = cfg['Estacion']['Nombre']
sensor = cfg['Estacion']['Sensor']

# FTP
servidor = cfg['FTP']['Servidor']
usuario = cfg['FTP']['Usuario']
passw = cfg['FTP']['Pass']
carpeta = cfg['FTP']['Carpeta']

ftp = sst_server.SST_Servidor(
    servidor=servidor,
    usuario=usuario,
    psw=passw,
    root=carpeta
)

# Iniciamos el servidor web local con flask
web_server = Flask(__name__)

# Gestiona las peticiones POST enviadas al servidor web

@web_server.route('/')
def hello_world():
    return 'Hello, World!'

@web_server.route("/", methods=['POST'])
def webhook():
    # si el POST recibido es un json
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(
            request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200


bot = telebot.TeleBot(TOKEN_TELEGRAM_BOT)

# Decorador para verificar si el usuario está autorizado


def usuario_autorizado(func):
    def verificar_usuario(message):
        user_id = message.from_user.id
        username = message.chat.username
        if str(user_id) in w_list or username in w_list:
            func(message)
        else:
            if message.chat.username is None:
                bot.reply_to(
                    message, f"Debe establecer un nombre de usuario Telegram para continuar", parse_mode="HTML")
            else:
                bot.reply_to(
                    message, "Lo siento, no estás autorizado para ejecutar este comando.")
                logging.error(
                    f"El usuario {message.chat.username} con ID: {message.from_user.id} fue rechazado")
                mensaje = f"Solicitud del usuario {message.chat.username} ID: {message.from_user.id}"
                bot.send_message(5421431478, mensaje)
    return verificar_usuario

# Decorador para verificar si el usuario es el administrador


def is_admin(func):
    def verificar_admin(message):
        user_id = message.from_user.id
        username = message.chat.username
        if str(user_id) in user_id_admin or username in user_admin:
            authorized = True
            func(message, authorized)
        else:
            authorized = False
            if func.__name__ != 'cmd_botones':
                bot.send_message(
                    message.chat.id, "Lo siento, no estás autorizado para ejecutar este comando.")
                logging.error(
                    f"El usuario {message.chat.username} con ID: {message.from_user.id} fue rechazado")
            func(message, authorized)
    return verificar_admin


@bot.message_handler(commands=["start"])
@usuario_autorizado
def cmd_start(message):
    cadena = f'Bienvenido <b>{message.chat.username}</b>\n'
    cadena += f'Soy SST_Bot, en que puedo ayudarlo?' + '\n\n'
    cadena += f'Menu de opciones' + '\n'
    time.sleep(0.25)
    """ Muestra un mensaje con los botonos de comandos inline (dentro del chat) """
    markup = InlineKeyboardMarkup(
        row_width=2)              # Botones por linea por defecto 3
    btn_estaciones = InlineKeyboardButton(
        "Ver Estaciones", callback_data="estaciones")
    btn_ayuda = InlineKeyboardButton("Información", callback_data="info")
    btn_cerrar = InlineKeyboardButton("Cerrar", callback_data="cerrar")
    markup.add(btn_estaciones, btn_ayuda, btn_cerrar)
    bot.send_message(message.chat.id, cadena,
                     parse_mode="HTML", reply_markup=markup)


@bot.message_handler(commands=["help"])
@usuario_autorizado
def cmd_help(message):
    bot.reply_to(message, "Hola!!! Soy SST_Bot, en que puedo ayudarlo?")
    comandos = bot.get_my_commands()
    cadena = ""
    if message.chat.username in user_admin:
        for comando in comandos:
            cadena += f"*/{comando.command}*\tDescripción: {comando.description}\n"
    else:
        for comando in comandos:
            if comando.command in w_cmd_lit:
                cadena += f"*/{comando.command}*\tDescripción: {comando.description}\n"

    bot.send_message(message.chat.id, cadena, parse_mode="MarkdownV2")


@bot.message_handler(commands=["info"])
@usuario_autorizado
def cmd_info(message):
    cadena = __GetInfo()
    bot.send_message(message.chat.id, cadena, parse_mode="MarkdownV2")


@bot.message_handler(commands=["alta"])
@is_admin
def cmd_alta(message, authorized):
    if authorized:
        markup = ForceReply()
        msg = bot.send_message(
            message.chat.id, "Nombre del nuevo usuario:", reply_markup=markup)
        bot.register_next_step_handler(msg, nuevo_usuario)


@bot.message_handler(commands=["baja"])
@is_admin
def cmd_baja(message, authorized):
    if authorized:
        markup = ForceReply()
        msg = bot.send_message(
            message.chat.id, "Nombre del usuario a eliminar:", reply_markup=markup)
        bot.register_next_step_handler(msg, baja_usuario)


def nuevo_usuario(message):
    usuario = message.text
    logging.info(f"Se ah eliminado el usuario {usuario}")
    bot.send_message(
        message.chat.id, f'Usuario *{usuario}* eliminado', parse_mode="MarkdownV2")


def baja_usuario(message):
    usuario = message.text
    logging.info(f"Se ah dado de alta un nuevo usuario: {usuario}")
    bot.send_message(
        message.chat.id, f'Usuario *{usuario}* eliminado', parse_mode="MarkdownV2")


@bot.message_handler(commands=["bot_estaciones"])
@is_admin
def cmd_botones(message, authorized):
    global estaciones, estacion_seleccionada
    """ Muestra un mensaje con los botonos de comandos inline (dentro del chat) """
    if authorized:
        url = "https://sst-api-ac6y.onrender.com/actualizar-ftp_admins"
    else:
        url = "https://sst-api-ac6y.onrender.com/actualizar-ftp"
    ftp_file_json = requests.get(url)
    if ftp_file_json.status_code != 200:
        print()
    estaciones = ftp_file_json.json()
    estaciones['estaciones'] = ast.literal_eval(estaciones['estaciones'])
    estaciones = estaciones['estaciones']
    # Botones por linea por defecto 3
    markup = InlineKeyboardMarkup(row_width=2)
    # Crear botones dinámicamente según la información del archivo JSON
    for key, value in estaciones.items():
        callback_data = f"{key}"
        button = InlineKeyboardButton(key, callback_data=callback_data)
        markup.add(button)
    button = InlineKeyboardButton("Cerrar", callback_data="cerrar")
    markup.add(button)
    bot.send_message(
        message.chat.id, "🌡Selecciona una Estacion de monitoreo", reply_markup=markup)


@bot.message_handler(commands=["bot_Accion"])
@usuario_autorizado
def cmd_btn_aciones(message):
    """ Muestra un mensaje con los botonos de comandos inline (dentro del chat) """
    markup = InlineKeyboardMarkup(
        row_width=2)              # Botones por linea por defecto 3
    btn_estaciones = InlineKeyboardButton(
        "Ver Estaciones", callback_data="estaciones")
    btn_ayuda = InlineKeyboardButton("Ayuda", callback_data="ayuda")
    btn_cerrar = InlineKeyboardButton("Cerrar", callback_data="cerrar")
    markup.add(btn_estaciones, btn_ayuda, btn_cerrar)
    bot.send_message(message.chat.id, "Menu de opciones", reply_markup=markup)


@bot.callback_query_handler(func=lambda x: True)
def repuesta_botones_inline(call):
    """Gestiono las acciones de los botones inline"""
    global estaciones, estacion_seleccionada
    chat_id = call.from_user.id
    message_id = call.message.id
    username = call.from_user.username
    if call.data in set(estaciones):
        estacion_seleccionada = call.data
        mostrar_info_estacion(chat_id, message_id, username)
    elif call.data == "estaciones":
        estacion_seleccionada = None
        bot.delete_message(chat_id, message_id)
        cmd_botones(call.message)
    elif call.data == "cerrar":
        bot.delete_message(chat_id, message_id)
        cmd_start(call.message)
    elif call.data == "volver":
        estacion_seleccionada = None
        bot.delete_message(chat_id, message_id)
        cmd_botones(call.message)
    elif call.data == 'info':
        estacion_seleccionada = None
        bot.delete_message(chat_id, message_id)
        cmd_info(call.message)


def mostrar_info_estacion(chat_id, message_id, username):
    global estacion_seleccionada
    if estacion_seleccionada in estaciones:
        estacion = estaciones.get(estacion_seleccionada)
        mensaje = f"<b>Información de la Estación {estacion_seleccionada}</b> ❌\n\n"
        if estacion['info']['estado']:
            mensaje = f"<b>Información de la Estación {estacion_seleccionada}</b> ✅\n\n"
        latitud = "{:.3f}".format(estacion['Posicion'][0])
        longitud = "{:.3f}".format(estacion['Posicion'][1])
        actualizado = estacion['date_update']
        for clave, valor in estacion.items():
            if clave != "info" and clave != "date_update" and clave != "Posicion":
                mensaje += f"<b>{clave}:</b> {valor}\n"
        mensaje += f"<b>Ultima actualización:</b> {actualizado}\n"
        valor = f"<b>Ultimo registro:</b> {estacion['info']['fecha']} {estacion['info']['hora']}\n<b>Valor:</b> {estacion['info']['dato']}\n"
        mensaje += valor
        mensaje += f"<b>Coordenadas:</b> [{latitud}, {longitud}]\n"
        mensaje += f" <a href='https://www.google.com/maps?q={estacion['Posicion'][0]},{estacion['Posicion'][1]}'>Coordenadas</a>"
        # Botón para volver al menú de estaciones
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(
            "Volver a la lista de estaciones", callback_data="volver"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=mensaje, parse_mode="HTML", reply_markup=markup)
        logging.info(
            f"Consulta realizada sobre la estacion {estacion_seleccionada} por {username}")
    else:
        bot.send_message(
            chat_id, "Información no encontrada para esta estación.")


@bot.message_handler(content_types=["text"])
@usuario_autorizado
def bot_mensajes_texto(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "comando invalido")
    else:
        bot.send_message(
            message.chat.id, "Consulte los comandos disponibles para interactuar \help")


def GetFolderJSON(archivo):
    with open(archivo, 'wb') as local_file:
        ftp.retrbinary('RETR ' + archivo, local_file.write)


def __GetInfo():
    cadena = f'*SST Bot*\n'
    cadena += f"Aplicacion para comunicacion con las estaciones de monitoreo de la red de sensoramiento de temperatura superficial del mar\n"
    cadena += f'*Desarrollador:* {__author__}' + '\n'
    cadena += f'*Version:*{__version__}' + '\n'
    cadena += f'*Update:* {__date__}' + '\n'
    return cadena




def enviar_mensaje(access='users'):
    # Función para enviar el mensaje
    url = "https://sst-api-ac6y.onrender.com/actualizar-ftp_admins"
    ftp_file_json = requests.get(url)
    if ftp_file_json.status_code != 200:
        print()
    estaciones = ftp_file_json.json()
    estaciones['estaciones'] = ast.literal_eval(estaciones['estaciones'])
    estaciones = estaciones['estaciones']

    # Recorro estacion por estacion
    for i in estaciones:
        # Mensaje a enviar
        estacion = estaciones[i]
        ico = f"⚠️"
        if estacion['info']['estado']:
            ico = f"✅"
        mensaje = f"{ico} Reporte diario, estado de las estaciones de monitoreo de temperatura.\n\n"
        mensaje += f"<b>Estado de la estacion</b> {estacion['Nombre']}\n"
        mensaje += f"<b>Ultima actualización:</b> {estacion['date_update']}\n"
        mensaje += f"<b>Ultimo registro:</b> {estacion['info']['fecha']} {estacion['info']['hora']}\n"
        valor = "{:.3f}".format(float(estacion['info']['dato']))
        mensaje += f"<b>Valor:</b> {valor}\n"

        # ID del chat al que quieres enviar el mensaje
        for chat_id in user_id_admin:
            # Enviar el mensaje al chat específico
            bot.send_message(chat_id, mensaje, parse_mode="HTML")


def enviar_mensaje_admins():
    enviar_mensaje(access='admin')

# Función para programar el mensaje diario


def programar_mensaje():
    schedule.every().day.at("08:00").do(enviar_mensaje)
    schedule.every().day.at("20:00").do(enviar_mensaje_admins)
    schedule.every(10).minutes.do(enviar_mensaje)


# Ejecutar la programación del mensaje al inicio
programar_mensaje()

# Función para ejecutar el schedule


def ejecutar_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)


# Ejecutar el schedule en un hilo aparte
schedule_thread = threading.Thread(target=ejecutar_schedule)
schedule_thread.start()

if __name__ == "__main__":
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Inicia el BOT"),
        telebot.types.BotCommand("/help", "Lista los comandos"),
        telebot.types.BotCommand("/info", "Información del bot"),
    ])
    time.sleep(1)
    print(f"BOT SST Telegram iniciado version {__version__}")
    # Iniciar el servidor Flask
    serve(web_server, host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
    web_server.run(debug=True)
