import os
import sys
import datetime
import logging
import json
import time
import threading
import requests

import telebot
from telebot.types import ForceReply
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
import schedule

from flask import Flask, request                # Para crear nuestro servidor web propio LOCAL
from pyngrok import ngrok, conf                 # Creo el nexo entre nuestro servidor web local y el bot de telegram
from waitress import serve

from modulos import sst_server
from modulos.utils import *

__version__ = "V 1 0"
__date__ = "2023/12/12"
__author__ = "Cubiella, Alvaro"

global ftp_file_json, estacion_seleccionada

ftp_file_json = {}
estacion_seleccionada = None

# Establezco a partir de que nivel se imprimen los mensajes y formato
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s -  %(processName)s - %(levelname)s - %(message)s",
                    filename= 'Telegram_BOT.log',
                    filemode= 'a')

file = f"{os.getcwd()}{os.sep}T_Bot.json"

try:
    with open(file, 'r') as f:  
        cfg = json.load(f)  
except:
    logging.critical(f"No se pudo cargar el archivo de configuracion {file}")
    sys.exit(0)

#Estacion
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
    psw = passw,
    root= carpeta
)

# Iniciamos el servidor web local con flask
web_server = Flask(__name__)

# Gestiona las peticiones POST enviadas al servidor web
@web_server.route("/", methods = ['POST'])
def webhook():
    # si el POST recibido es un json
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200

#ftp.Conectar()
#ftp.GetFile(file='MdPSBE3820231211.txt')

user_id_admin = (
    5421431478,
    )
user_admin = (
    'AlvaroCubiella',
    )

w_list=(
    'AlvaroCubiella',
    'EmmanuelZel',
    'NoeManik4',
    'Raul_Reta',
    )

# Lista de comandos para usuarios
w_cmd_lit = (
    'start',
    'info',
    'help',
    )

bot = telebot.TeleBot(TOKEN_TELEGRAM_BOT)

# Decorador para verificar si el usuario está autorizado
def usuario_autorizado(func):
    def verificar_usuario(message):
        user_id = message.from_user.id
        username = message.chat.username
        if str(user_id) in w_list or username in w_list:
            func(message)
        else:
            bot.reply_to(message, "Lo siento, no estás autorizado para ejecutar este comando.")
            logging.error(f"El usuario {message.chat.username} con ID: {message.from_user.id} fue rechazado")
    return verificar_usuario

# Decorador para verificar si el usuario es el administrador
def is_admin(func):
    def verificar_admin(message):
        user_id = message.from_user.id
        username = message.chat.username
        if str(user_id) in user_id_admin or username in user_admin:
            func(message)
        else:
            bot.reply_to(message, "Lo siento, no estás autorizado para ejecutar este comando.")
            logging.error(f"El usuario {message.chat.username} con ID: {message.from_user.id} fue rechazado")
    return verificar_admin

@bot.message_handler(commands=["start"])
@usuario_autorizado
def cmd_start(message):
    if not message.chat.username in w_list:
        bot.reply_to(message.chat.id, f"Hola <b>{message.chat.username}</b>\nLamentablemente no dispone de los privilegios para poder asistirlo", parse_mode="HTML")
        bot.kick_chat_member(message.chat.id, message.from_user.id)
    else:
        cadena = f'Bienvenido <b>{message.chat.username}</b>\n'
        cadena += f'Soy SST_Bot, en que puedo ayudarlo?' + '\n\n'
        cadena += f'Menu de opciones' + '\n'
        #bot.send_message(message.chat.id, cadena, parse_mode="HTML")
        time.sleep(0.25)
        """ Muestra un mensaje con los botonos de comandos inline (dentro del chat) """
        markup = InlineKeyboardMarkup(row_width=2)              # Botones por linea por defecto 3
        btn_estaciones = InlineKeyboardButton("Ver Estaciones", callback_data="estaciones")
        btn_ayuda = InlineKeyboardButton("Ayuda", callback_data="ayuda")
        btn_cerrar = InlineKeyboardButton("Cerrar", callback_data="cerrar")
        markup.add(btn_estaciones, btn_ayuda, btn_cerrar)
        bot.send_message(message.chat.id, cadena, parse_mode="HTML", reply_markup=markup)

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
    bot.reply_to(message, cadena, parse_mode="MarkdownV2")

@bot.message_handler(commands=["alta"])
@is_admin
def cmd_alta(message):
    markup = ForceReply()
    msg = bot.send_message(message.chat.id, "Nombre del nuevo usuario:", reply_markup = markup)
    bot.register_next_step_handler(msg, nuevo_usuario)

@bot.message_handler(commands=["baja"])
@is_admin
def cmd_baja(message):
    markup = ForceReply()
    msg = bot.send_message(message.chat.id, "Nombre del usuario a eliminar:", reply_markup = markup)
    bot.register_next_step_handler(msg, baja_usuario)

def nuevo_usuario(message):
    usuario = message.text
    logging.info(f"Se ah eliminado el usuario {usuario}")
    bot.send_message(message.chat.id, f'Usuario *{usuario}* eliminado', parse_mode="MarkdownV2")

def baja_usuario(message):
    usuario = message.text
    logging.info(f"Se ah dado de alta un nuevo usuario: {usuario}")
    bot.send_message(message.chat.id, f'Usuario *{usuario}* eliminado', parse_mode="MarkdownV2")

@bot.message_handler(commands=["bot_estaciones"])
@usuario_autorizado
def cmd_botones(message):
    global ftp_file_json, estacion_seleccionada
    """ Muestra un mensaje con los botonos de comandos inline (dentro del chat) """
    ftp.Conectar()
    carpetas = ftp.GetFolders()
    ftp_file_json = ftp.ReadFile(ftp.root, file='folders.json')
    markup = InlineKeyboardMarkup(row_width=2)              # Botones por linea por defecto 3
    # Crear botones dinámicamente según la información del archivo JSON
    for key, value in ftp_file_json.items():
        callback_data = f"{key}"
        button = InlineKeyboardButton(key, callback_data=callback_data)
        markup.add(button)
    button = InlineKeyboardButton("Cerrar", callback_data="cerrar")
    markup.add(button)
    bot.send_message(message.chat.id, "🌡Selecciona una Estacion de monitoreo", reply_markup=markup)

@bot.message_handler(commands=["bot_Accion"])
@usuario_autorizado
def cmd_btn_aciones(message):
    """ Muestra un mensaje con los botonos de comandos inline (dentro del chat) """
    markup = InlineKeyboardMarkup(row_width=2)              # Botones por linea por defecto 3
    btn_estaciones = InlineKeyboardButton("Ver Estaciones", callback_data="estaciones")
    btn_ayuda = InlineKeyboardButton("Ayuda", callback_data="ayuda")
    btn_cerrar = InlineKeyboardButton("Cerrar", callback_data="cerrar")
    markup.add(btn_estaciones, btn_ayuda, btn_cerrar)
    bot.send_message(message.chat.id, "Menu de opciones", reply_markup=markup)

@bot.callback_query_handler(func= lambda x: True)
def repuesta_botones_inline(call):
    """Gestiono las acciones de los botones inline"""
    global ftp_file_json, estacion_seleccionada
    chat_id = call.from_user.id
    message_id = call.message.id
    username = call.from_user.username
    if call.data in set(ftp_file_json):
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

def mostrar_info_estacion(chat_id, message_id, username):
    global estacion_seleccionada
    if estacion_seleccionada in ftp_file_json:
        info_estacion = ftp_file_json.get(estacion_seleccionada)
        mensaje = f"<b>Información de la Estación {estacion_seleccionada}</b>\n\n"
        latitud = info_estacion['Posicion'][0]
        longitud = info_estacion['Posicion'][1]
        fecha = datetime.datetime.now().date()
        file = f"{estacion_seleccionada}{info_estacion.get('Sensor')}{fecha.year}{fecha.month}{fecha.day}.txt"
        ftp.Conectar()
        ftp_file = ftp.ReadFiletxt(f"{ftp.root}/{estacion_seleccionada}", file=file)
        ftp.close()
        for clave, valor in info_estacion.items():
            mensaje += f"<b>{clave}:</b> {valor}\n"
        scan = ftp_file[-1].split(",")
        valor = f"<b>Ultimo registro:</b> {scan[1]}\n<b>Valor:</b> {scan[2]}\n"
        mensaje += valor
        # <a href="https://www.Tecnonucleous.com/">Tecnonucleous</a>
        mensaje += f" <a href='https://www.google.com/maps?q={latitud},{longitud}'>Coordenadas</a>"
        # Botón para volver al menú de estaciones
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Volver a la lista de estaciones", callback_data="volver"))
        # <a href="https://www.Tecnonucleous.com/">Tecnonucleous</a>
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=mensaje, parse_mode="HTML", reply_markup=markup)
        logging.info(f"Consulta realizada sobre la estacion {estacion_seleccionada} por {username}")
    else:
        bot.send_message(chat_id, "Información no encontrada para esta estación.")
    
@bot.message_handler(content_types=["text"])
@usuario_autorizado
def bot_mensajes_texto(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "comando invalido")
    else:
        bot.send_message(message.chat.id, "Consulte los comandos disponibles para interactuar \help")

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

# Función para programar el mensaje diario
def programar_mensaje():
    #schedule.every().day.at("08:00").do(cmd_start)
    schedule.every().minute.do(cmd_start)

# Ejecutar la programación del mensaje al inicio
programar_mensaje()

# Función para ejecutar el schedule
def ejecutar_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Ejecutar el schedule en un hilo aparte
#schedule_thread = threading.Thread(target=ejecutar_schedule)
#schedule_thread.start()

if __name__ == "__main__":
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Inicia el BOT"),
        telebot.types.BotCommand("/help", "Lista los comandos"),
        telebot.types.BotCommand("/info", "Información del bot"),
        ])
    time.sleep(1)
    print(f"BOT SST Telegram iniciado version {__version__}")
    conf.get_default().config_path = ".//config_ngrok.yml"
    # REGIONES DISPONIBLES:
    # us - United States
    # eu - Europe
    # ap - Asia
    # sa - South America (Sao Paulo)
    conf.get_default().region = "sa" 
    # creamos el archivo de credenciales de la API ngrok
    ngrok.set_auth_token(NGORK_TOKEN)
    # Creamos un TUNEL https en el puerto 5000 para conectar ngrok con flask
    ngrok_tunel = ngrok.connect(5000, bind_tls = True)
    # url del tunel https creado
    ngrok_url = ngrok_tunel.public_url
    # eliminamos el webhook
    bot.remove_webhook()
    # hacemos una pausa para que lo termine de eliminar y no genere conflictos
    time.sleep(1)
    # definimos el nuevo webhook
    bot.set_webhook(url=ngrok_url)
    # Finalmente iniciamos el servidor
    serve(web_server, host="0.0.0.0", port = 5000)




    #bot.infinity_polling(none_stop=True)