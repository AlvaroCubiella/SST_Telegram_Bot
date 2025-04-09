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

# Variables globales
global estaciones, estacion_seleccionada
global user_id_admin

estaciones = {}
estacion_seleccionada = None
user_admin = ()
user_id_admin = (5421431478,)  # Asegúrate de usar la lista de IDs correcta
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

# Intento cargar el archivo de configuración
try:
    with open(file, 'r') as f:
        cfg = json.load(f)
except:
    logging.critical(f"No se pudo cargar el archivo de configuracion {file}")
    sys.exit(0)

# Estación y configuración FTP
estacion = cfg['Estacion']['Nombre']
sensor = cfg['Estacion']['Sensor']
servidor = cfg['FTP']['Servidor']
usuario = cfg['FTP']['Usuario']
passw = cfg['FTP']['Pass']
carpeta = cfg['FTP']['Carpeta']

ftp = sst_server.SST_Servidor(servidor=servidor,
                              usuario=usuario, psw=passw, root=carpeta)

# Configura el Webhook


def set_telegram_webhook():
    webhook_url = "https://sst-telegram-bot.onrender.com/"  # Aquí tu URL pública
    webhook_api_url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM_BOT}/setWebhook?url={webhook_url}"

    response = requests.get(webhook_api_url)
    if response.status_code == 200:
        print("Webhook configurado correctamente.")
    else:
        print("Error al configurar el Webhook:", response.text)


# Llama a la función para configurar el Webhook
set_telegram_webhook()

# Inicializa el bot
bot = telebot.TeleBot(TOKEN_TELEGRAM_BOT)

# Funciones de manejo de usuarios y comandos


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

# Definición de las rutas y comandos del bot (igual que tu código original)

# Rutas y manejadores de comandos...
# (Aquí sigue el resto del código que ya tienes, sin cambios.)


# Servidor Flask
web_server = Flask(__name__)


@web_server.route('/hello')
def hello_world():
    return 'Hello, World!'


@web_server.route("/", methods=['POST'])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(
            request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200


# Ejecuta el servidor Flask
if __name__ == "__main__":
    bot.set_my_commands([  # Comandos del bot
        telebot.types.BotCommand("/start", "Inicia el BOT"),
        telebot.types.BotCommand("/help", "Lista los comandos"),
        telebot.types.BotCommand("/info", "Información del bot"),
    ])
    time.sleep(1)
    print(f"BOT SST Telegram iniciado version {__version__}")
    # Inicia el servidor Flask con waitress
    serve(web_server, host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
    web_server.run(debug=True)
