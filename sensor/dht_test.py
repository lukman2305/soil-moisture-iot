import time
import board
import adafruit_dht
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import adafruit_dht

dht=adafruit_dht.DHT11(board.D4)
i2c = busio.I2C(board.SCL, board.SDA)
oled=adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

oled.fill(0)
oled.show()

img= Image.new("1", (oled.width,oled.height))
draw = ImageDraw.Draw(img)
font=ImageFont.load_default()

print("System active.. Press Ctrl+C to stop.")

while True:
	try:
		temperature=dht.temperature
		humidity=dht.humidity
		print(f"Temp: {temperature} C Humidity: {humidity}%")
		draw.rectangle((0,0, oled.width, oled.height), outline=0, fill=0)
		draw.text((0,0),"==== CLIMATE DATA ===", font=font, fill=255)
		draw.text((0,22),f"Temp: {temperature} C", font=font, fill=255)
		draw.text((0,38),f"Humid: {humidity}%,", font=font, fill=255)

		oled.image(img)
		oled.show()
	except RutimeErrOr as e:
		 print(f"Reading error: {e}")
	time.sleep(2)
