from os import path, remove, makedirs, rmdir, walk, rename
from tkinter.filedialog import askdirectory
from PIL import Image, ImageOps, ImageChops
from shutil import move, copy, copytree
from base64 import b64decode
from json import load, dumps
from tkinter import Tk
from io import BytesIO
from uuid import uuid4
from re import search
import sys

try:
	def resource_path(relative_path):
		try:
			base_path = sys._MEIPASS
		except Exception:
			base_path = path.abspath(".")

		return path.join(base_path, relative_path)

	def converter():
		gui=Tk().withdraw()

		directory = askdirectory(title = "Select Pack")
		if directory == "":
			input("No folder selected\nPress ENTER to quit...")
			sys.exit(0)

		version = input("Enter input version: ")
		userOutput = input("Enter output version: ")

		if version.lower() == "java" and userOutput.lower() == "bedrock":
			outputDirectory = f"{directory}_bedrock"
			if path.isdir(outputDirectory):
				input(f"Failed to convert. Output folder {outputDirectory} already exists")
				exit()
			makedirs(outputDirectory)
			conversionJSON = "java-bedrock.json"
			with open(resource_path(path.join("conversions", conversionJSON))) as jsonFile:
				data = load(jsonFile)
			try:
				mcmetaDir = path.join(directory, "pack.mcmeta")
				if path.isfile(mcmetaDir):
					with open(mcmetaDir) as mcmetaFile:
						mcmetaData = load(mcmetaFile)
					if not "description" in mcmetaData["pack"]:
						input("Failed to convert. pack.mcmeta missing description")
					manifestData = {
						"format_version": 2,
						"header": {
							"name": path.basename(directory),
							"description": mcmetaData["pack"]["description"],
							"uuid": str(uuid4()),
							"version": [0, 0, 1],
							"min_engine_version": [1, 17, 0]
						},
						"modules": [
							{
								"description": mcmetaData["pack"]["description"],
								"type": "resources",
								"uuid": str(uuid4()),
								"version": [0, 0, 1]
							}
						]
					}
					with open(f"{outputDirectory}/manifest.json", "w") as outputManifest:
						outputManifest.write(dumps(manifestData, indent = 2, ensure_ascii = False))
					print("Created manifest.json")
			except:
				input("Failed to convert. Couldn't read the pack.mcmeta")
				sys.exit()
		
			if path.isfile(f"{directory}/pack.png"):
				copyFile(f"{directory}/pack.png", f"{outputDirectory}/pack_icon.png")

			grassTintColour = (124, 189, 107)
			foliageTintColour = (91, 171, 70)
			print(grassTintColour, foliageTintColour)
			if path.isfile(f"{directory}/assets/minecraft/textures/colormap/grass.png"):
				img = Image.open(f"{directory}/assets/minecraft/textures/colormap/grass.png").convert("RGBA")
				if img.size == (256, 256):
					grassTintColour = img.getpixel((127, 127))[:3]
				else:
					print(f"Skipped sourcing tint colour from {directory}/assets/minecraft/textures/colormap/grass.png as it's size is invalid")
			if path.isfile(f"{directory}/assets/minecraft/textures/colormap/foliage.png"):
				img = Image.open(f"{directory}/assets/minecraft/textures/colormap/foliage.png").convert("RGBA")
				if img.size == (256, 256):
					foliageTintColour = img.getpixel((127, 127))[:3]
				else:
					print(f"Skipped sourcing tint colour from {directory}/assets/minecraft/textures/colormap/foliage.png as it's size is invalid")
			if "editing" in data:
				if "edit" in data["editing"]:
					for item in data["editing"]["edit"]:
						if isinstance(item["outputName"], list):
							outputNames = item["outputName"]
						else:
							outputNames = (item["outputName"],)
						if isinstance(item["inputName"], list):
							inputNames = item["inputName"]
						else:
							inputNames = (item["inputName"],)
						for x in range(len(outputNames)):
							texture = path.join(directory, inputNames[x % len(inputNames)])
							if path.isfile(texture):
								img = Image.open(texture).convert("RGBA")
								if img.size[0] // item["afterSize"]["w"] == img.size[1] // item["afterSize"]["h"]:
									m = img.size[1] / item["afterSize"]["h"]
									if "baseImage" in item:
										imgNew = Image.open(BytesIO(b64decode(item["baseImage"]))).convert("RGBA").resize((int(item["beforeSize"]["w"]*m), int(item["beforeSize"]["h"]*m)), Image.NEAREST)
									else:
										imgNew = Image.new("RGBA", (int(item["beforeSize"]["w"]*m), int(item["beforeSize"]["h"]*m)))
									for edit in item["edits"]:
										if "texture" in edit:
											if isinstance(edit["texture"], str):
												imgTemp = Image.open(f"{directory}/{edit['texture']}").convert("RGBA").crop((int(edit["newLocation"]["x"]*m), int(edit["newLocation"]["y"]*m), int(edit["newLocation"]["x"]*m)+int(edit["w"]*m), int(edit["newLocation"]["y"]*m)+int(edit["h"]*m))).convert("RGBA")
											else:
												imgTemp = Image.open(f"{directory}/{edit['texture'][x]}").convert("RGBA").crop((int(edit["newLocation"]["x"]*m), int(edit["newLocation"]["y"]*m), int(edit["newLocation"]["x"]*m)+int(edit["w"]*m), int(edit["newLocation"]["y"]*m)+int(edit["h"]*m))).convert("RGBA")
										else:
											imgTemp = img.crop((int(edit["newLocation"]["x"]*m), int(edit["newLocation"]["y"]*m), int(edit["newLocation"]["x"]*m)+int(edit["w"]*m), int(edit["newLocation"]["y"]*m)+int(edit["h"]*m)))
										if "flip" in edit and edit["flip"] == True:
											imgTemp = ImageOps.mirror(imgTemp)
										if "flipv" in edit and edit["flipv"] == True:
											imgTemp = ImageOps.flip(imgTemp)
										if "hue" in edit:
											imgTemp = hue(imgTemp, edit["hue"])
										if "tint" in edit:
											if isinstance(edit["tint"], str):
												tintVal = edit["tint"]
											else:
												tintVal = edit["tint"][x]
											if tintVal == "foliage":
												tintColour = foliageTintColour
											elif tintVal == "grass":
												tintColour = grassTintColour
											else:
												if isinstance(tintVal, str):
													col = tintVal.replace("#", "")
													tintColour = (int(col[:2], 16), int(col[2:4], 16), int(col[-2:], 16))
												else:
													tintColour = tintVal
											tint = Image.new("RGBA", imgTemp.size, (*tintColour, 255))
											imgTemp = ImageChops.multiply(imgTemp, tint)
										if "grayscale" in edit and edit["grayscale"]:
											imgTemp = imgTemp.convert("LA").convert("RGBA")
										if "rotate" in edit:
											imgTemp = imgTemp.rotate(-edit["rotate"], expand = True)
										if "opacity" in edit:
											imgTemp2 = Image.new("RGBA", imgTemp.size, (0, 0, 0, edit["opacity"]))
											imgNew.paste(imgTemp, (int(edit["oldLocation"]["x"]*m), int(edit["oldLocation"]["y"]*m)), imgTemp2)
										else:
											imgNew.paste(imgTemp, (int(edit["oldLocation"]["x"]*m), int(edit["oldLocation"]["y"]*m)), imgTemp)
									outputName = f"{outputDirectory}/{outputNames[x]}"
									outputPath = path.dirname(outputName)
									if not path.isdir(outputPath):
										makedirs(outputPath)
									imgNew.save(outputName)
									print(f"Created {outputName}")

				if "spritesheet" in data["editing"]:
					for spritesheet in data["editing"]["spritesheet"]:
						spritesheetTexture = path.join(outputDirectory, spritesheet)
						m = 0
						for item in data["editing"]["spritesheet"][spritesheet]["textures"]:
							fileDir = path.join(directory, item["fileName"])
							if path.isfile(fileDir):
								file = Image.open(fileDir).convert("RGBA")
								m = max(file.size[1] / item["h"], m)
						if not m == 0:
							img = Image.open(BytesIO(b64decode(data["editing"]["spritesheet"][spritesheet]["baseImage"]))).convert("RGBA").resize((int(data["editing"]["spritesheet"][spritesheet]["defaultSize"]["w"]*m), int(data["editing"]["spritesheet"][spritesheet]["defaultSize"]["h"]*m)), Image.NEAREST)
							for item in data["editing"]["spritesheet"][spritesheet]["textures"]:
								fileDir = path.join(directory, item["fileName"])
								if path.isfile(fileDir):
									file = Image.open(fileDir).resize((int(item["w"]*m), int(item["h"]*m)), Image.NEAREST).convert("RGBA")
									if "hue" in item:
										file = hue(file, item["hue"])
									if "grayscale" in item:
										if item["grayscale"] == 1:
											pixel = list(file.resize((1, 1)).getdata())[0]
											channels = file.split()
											channel = channels[pixel.index(max(*pixel[:3]))].convert("L")
											file = Image.merge("RGBA", (channel, channel, channel, channels[3]))
										elif item["grayscale"] == 0:
											file = file.convert("LA")
									img.paste(file, (int(item["x"]*m), int(item["y"]*m)))
							newDirectory = path.dirname(spritesheetTexture)
							if not path.exists(newDirectory):
								makedirs(newDirectory)
							img.save(spritesheetTexture)
							print(f"Created {spritesheetTexture}")

				if "chests" in data["editing"]:
					if "single" in data["editing"]["chests"]:
						for chest in data["editing"]["chests"]["single"]:
							chestDir = f"{directory}/assets/minecraft/textures/entity/chest/{chest}.png"
							if path.isfile(chestDir):
								outputChestDir = f"{outputDirectory}/textures/entity/chest"
								if not path.isdir(outputChestDir):
									makedirs(outputChestDir)
								singleChest(chestDir, True).save(f"{outputChestDir}/{chest}.png")
								print(f"Created {outputChestDir}/{chest}.png")
					if "double" in data["editing"]["chests"]:
						for chest in data["editing"]["chests"]["double"]:
							chestDir = f"{directory}/assets/minecraft/textures/entity/chest/{chest[0]}_left.png"
							chestDir2 = f"{directory}/assets/minecraft/textures/entity/chest/{chest[0]}_right.png"
							if path.isfile(chestDir) and path.isfile(chestDir2):
								outputChestDir = f"{outputDirectory}/textures/entity/chest"
								if not path.isdir(outputChestDir):
									makedirs(outputChestDir)
								doubleChestDowngrade(chestDir, chestDir2, True).save(f"{outputChestDir}/{chest[1]}.png")
								print(f"Created {outputChestDir}/{chest[1]}.png")

			if "files" in data:
				if "copy" in data["files"]:
					for (oldLocation, newLocation) in data["files"]["copy"]:
						oldLocation = path.join(directory, oldLocation)
						newLocation = path.join(outputDirectory, newLocation)
						if path.isfile(oldLocation) and not path.isfile(newLocation):
							newDirectory = path.dirname(newLocation)
							if not path.exists(newDirectory):
								makedirs(newDirectory)
							copyFile(oldLocation, newLocation)

				if "join" in data["files"]:
					for file in data["files"]["join"]:
						x = 0
						while path.isfile(f"{directory}/{file[0][:-4]}_{x:01}.png") or path.isfile(f"{directory}/{file[0][:-4]}_{x:02}.png"):
							x += 1
						if x != 0:
							w, h = Image.open(f"{directory}/{file[0][:-4]}_0.png" if path.isfile(f"{directory}/{file[0][:-4]}_0.png") else f"{directory}/{file[0][:-4]}_00.png").size
							newImg = Image.new("RGBA", (w, w*x))
							for y in range(x):
								if path.isfile(f"{directory}/{file[0][:-4]}_{y:01}.png"):
									tempFile = f"{directory}/{file[0][:-4]}_{y:01}.png"
								else:
									tempFile = f"{directory}/{file[0][:-4]}_{y:02}.png"
								img = Image.open(tempFile).convert("RGBA")
								newImg.paste(img, (0, w*y))
							filePath = f"{outputDirectory}/{path.dirname(file[1])}"
							if not path.isdir(filePath):
								makedirs(filePath)
							newImg.save(f"{outputDirectory}/{file[1]}")
							print(f"Created {outputDirectory}/{file[1]}")

				if "tga" in data["files"]:
					for item in data["files"]["tga"]:
						baseColour = 0
						if "baseColour" in item:
							baseColour = item["baseColour"]
						transparentColour = 0
						if "transparentColour" in item:
							transparentColour = item["transparentColour"]
						outputFolder = path.dirname(f"{outputDirectory}/{item['outputName']}")
						if len(item["textures"]) > 1:
							if path.isfile(f"{directory}/{item['textures'][0]}.png") and path.isfile(f"{directory}/{item['textures'][1]}.png"):
								img = cleanImage(Image.open(f"{directory}/{item['textures'][0]}.png").convert("RGBA"), transparentColour)
								img2 = cleanImage(Image.open(f"{directory}/{item['textures'][1]}.png").convert("RGBA"), transparentColour)
								if "holepunch" in item and item["holepunch"]:
									img2 = holepunch(img, img2)
								img = copyPixels(img, img2, baseColour)
								if not path.isdir(outputFolder):
									makedirs(outputFolder)
								img.save(f"{outputDirectory}/{item['outputName']}.tga")
								print(f"Created {outputDirectory}/{item['outputName']}.tga")
							else:
								if "backup" in item:
									if path.isfile(f"{directory}/{item['backup']}.png"):
										copyFile(f"{directory}/{item['backup']}.png", f"{outputDirectory}/{item['outputName']}.png")
						else:
							if path.isfile(f"{directory}/{item['textures'][0]}.png"):
								img = cleanImage(Image.open(f"{directory}/{item['textures'][0]}.png").convert("RGBA"), transparentColour)
								img2 = Image.new("RGBA", img.size, (transparentColour, transparentColour, transparentColour, 255))
								img = copyPixels(img2, img, baseColour)
								if not path.isdir(outputFolder):
									makedirs(outputFolder)
								img.save(f"{outputDirectory}/{item['outputName']}.tga")
								print(f"Created {outputDirectory}/{item['outputName']}.tga")

			sheep = f"{outputDirectory}/textures/entity/sheep/sheep_temp.png"
			if path.isfile(sheep):
				sheepImg = Image.open(sheep).convert("RGBA")
				blankImg = Image.new("RGBA", sheepImg.size)
				blankImg.paste(sheepImg.crop((0, 0, sheepImg.size[0], sheepImg.size[1] // 2)))
				blankImg2 = Image.new("RGBA", sheepImg.size)
				blankImg2.paste(sheepImg.crop((0, sheepImg.size[1] // 2, sheepImg.size[0], sheepImg.size[1])), (0, sheepImg.size[1] // 2))
				img = cleanImage(blankImg, 255)
				img2 = cleanImage(blankImg2, 255)
				img = copyPixels(img, img2, baseColour)
				img.save(f"{outputDirectory}/textures/entity/sheep/sheep.tga")
				print(f"Created {outputDirectory}/textures/entity/sheep/sheep.tga")
				removeFile(sheep)

			if path.isfile(f"{outputDirectory}/textures/entity/chest/normal.png"):
				img = Image.open(f"{outputDirectory}/textures/entity/chest/normal.png").convert("RGBA")
				chestFront(img).save(f"{outputDirectory}/textures/blocks/chest_front.png")
				print(f"Created {outputDirectory}/textures/blocks/chest_front.png")
				chestSide(img).save(f"{outputDirectory}/textures/blocks/chest_side.png")
				print(f"Created {outputDirectory}/textures/blocks/chest_side.png")
				chestTop(img).save(f"{outputDirectory}/textures/blocks/chest_top.png")
				print(f"Created {outputDirectory}/textures/blocks/chest_top.png")

			if path.isfile(f"{outputDirectory}/textures/entity/chest/ender.png"):
				img = Image.open(f"{outputDirectory}/textures/entity/chest/ender.png").convert("RGBA")
				chestFront(img).save(f"{outputDirectory}/textures/blocks/ender_chest_front.png")
				print(f"Created {outputDirectory}/textures/blocks/ender_chest_front.png")
				chestSide(img).save(f"{outputDirectory}/textures/blocks/ender_chest_side.png")
				print(f"Created {outputDirectory}/textures/blocks/ender_chest_side.png")
				chestTop(img).save(f"{outputDirectory}/textures/blocks/ender_chest_top.png")
				print(f"Created {outputDirectory}/textures/blocks/ender_chest_top.png")

			if path.isfile(f"{outputDirectory}/textures/entity/chest/trapped.png"):
				img = Image.open(f"{outputDirectory}/textures/entity/chest/normal.png").convert("RGBA")
				chestFront(img).save(f"{outputDirectory}/textures/blocks/trapped_chest_front.png")
				print(f"Created {outputDirectory}/textures/blocks/trapped_chest_front.png")

			images = redstone(directory, False, True)
			if not images == None:
				images[0].save(f"{outputDirectory}/textures/blocks/redstone_dust_line.png")
				print(f"Created {outputDirectory}/textures/blocks/redstone_dust_line.png")
				if images[1] != None:
					images[1].save(f"{outputDirectory}/textures/blocks/redstone_dust_cross.png")
					print(f"Created {outputDirectory}/textures/blocks/redstone_dust_cross.png")

		else:
			if not version.split(".")[0] == "1" or not userOutput.split(".")[0] == "1":
				input("Invalid version\nPress ENTER to quit...")
				sys.exit(0)
			try:
				version = f"{version.split('.')[0]}.{int(version.split('.')[1])}"
				if int(version.split(".")[1]) < int(userOutput.split(".")[1]):
					upgrade = True
					outputVersion = f"{version.split('.')[0]}.{int(version.split('.')[1])+1}"
					print("Mode set to upgrade")
				elif int(version.split(".")[1]) > int(userOutput.split(".")[1]):
					upgrade = False
					outputVersion = f"{version.split('.')[0]}.{int(version.split('.')[1])-1}"
					print("Mode set to downgrade")
				else:
					input("Both versions cannot be the same\nPress ENTER to quit...")
					sys.exit(0)
			except:
				input("Invalid version\nPress ENTER to quit...")
				sys.exit(0)

			outputDirectory = f"{directory}_{userOutput}"

			print("Copying pack...")

			copytree(directory, outputDirectory)

			emissiveString = None
			emissiveDirectory = None
			emissiveDir = path.join(outputDirectory, "assets/minecraft/optifine/emissive.properties")
			altEmissiveDir = path.join(outputDirectory, "assets/minecraft/mcpatcher/emissive.properties")
			if path.isfile(emissiveDir):
				emissiveDirectory = emissiveDir
			elif path.isfile(altEmissiveDir):
				emissiveDirectory = altEmissiveDir
			if emissiveDirectory != None:
				try:
					with open(emissiveDirectory) as propertiesFile:
						emissiveString = search("suffix.emissive=(.+)", propertiesFile.read()).group(1)
					print(f'Emissive extention found and set as: {emissiveString}')
				except:
					print("Invalid emissive.properties. Skipping...")

			if upgrade == True:
				outputCheck = f"{userOutput.split('.')[0]}.{int(userOutput.split('.')[1])+1}"
			else:
				outputCheck = f"{userOutput.split('.')[0]}.{int(userOutput.split('.')[1])-1}"

			while not outputVersion == outputCheck:
				print(f"\n\n\nConverting from {version} to {outputVersion}\n\n\n")
				
				if upgrade == True:
					conversionJSON = f"{version}-{outputVersion}.json"
				else:
					conversionJSON = f"{outputVersion}-{version}.json"

				with open(resource_path(path.join("conversions", conversionJSON))) as jsonFile:
					data = load(jsonFile)

				if "pack_format" in data:
					mcmetaDir = path.join(outputDirectory, "pack.mcmeta")
					if path.isfile(mcmetaDir):
						try:
							with open(mcmetaDir) as json_file:
									packMcmeta = load(json_file)
							if upgrade == True:
								packMcmeta["pack"]["pack_format"] = data["pack_format"]["new"]
								print(f'Set pack format as: {data["pack_format"]["new"]}')
							else:
								packMcmeta["pack"]["pack_format"] = data["pack_format"]["old"]
								print(f'Set pack format as: {data["pack_format"]["old"]}')
				
							with open(f"{outputDirectory}/pack.mcmeta", "w") as out_file:
								out_file.write(dumps(packMcmeta, indent = 2, ensure_ascii = False))
						except:
							print("Failed to edit pack.mcmeta due to invalid JSON")

				if "special" in data:
					if "chests" in data["special"]:
						chests(outputDirectory, upgrade, emissiveString)
					if "mojang" in data["special"]:
						mojang(outputDirectory, upgrade)
					if "leaves" in data["special"]:
						leaves(outputDirectory, upgrade, emissiveString)
					if "redstone" in data["special"]:
						redstone(outputDirectory, upgrade)
					if "gui7" in data["special"]:
						gui7(outputDirectory, upgrade)
					if "gui8" in data["special"]:
						gui8(outputDirectory, upgrade)
					if "optifine" in data["special"]:
						optifineFolder = path.join
						optifineDir = path.join(outputDirectory, "assets/minecraft/optifine")
						mcpatcherDir = path.join(outputDirectory, "assets/minecraft/mcpatcher")
						if upgrade == False:
							if path.isdir(optifineDir) and not path.isdir(mcpatcherDir):
								rename(optifineDir, mcpatcherDir)
								print(f"Renamed the optifine folder to mcpatcher")
						else:
							if path.isdir(mcpatcherDir) and not path.isdir(optifineDir):
								rename(mcpatcherDir, optifineDir)
								print(f"Renamed the mcpatcher folder to optifine")

				if "editing" in data:
					if "spritesheet" in data["editing"]:
						for spritesheet in data["editing"]["spritesheet"]:
							spritesheetTexture = path.join(outputDirectory, spritesheet)
							if upgrade == True:
								if path.isfile(spritesheetTexture):
									img = Image.open(spritesheetTexture).convert("RGBA")
									w, h = img.size
									m = h / data["editing"]["spritesheet"][spritesheet]["defaultSize"]["h"]
									for item in data["editing"]["spritesheet"][spritesheet]["textures"]:
										texture = item["fileName"]
										try:
											file = img.crop((item["x"]*m, item["y"]*m, item["x"]*m+item["w"]*m, item["y"]*m+item["h"]*m))
											fileDir = path.join(outputDirectory, texture)
											newDirectory = path.dirname(fileDir)
											if not path.exists(newDirectory):
												makedirs(newDirectory)
											file.save(fileDir)
											print(f"Created {fileDir}")
										except:
											print(f"Failed to convert painting {file}")
							else:
								m = 0
								for item in data["editing"]["spritesheet"][spritesheet]["textures"]:
									fileDir = path.join(outputDirectory, item["fileName"])
									if path.isfile(fileDir):
										file = Image.open(fileDir).convert("RGBA")
										m = max(file.size[1] / item["h"], m)
								if not m == 0:
									img = Image.open(BytesIO(b64decode(data["editing"]["spritesheet"][spritesheet]["baseImage"]))).convert("RGBA").resize((int(data["editing"]["spritesheet"][spritesheet]["defaultSize"]["w"]*m), int(data["editing"]["spritesheet"][spritesheet]["defaultSize"]["h"]*m)), Image.NEAREST)
									for item in data["editing"]["spritesheet"][spritesheet]["textures"]:
										fileDir = path.join(outputDirectory, item["fileName"])
										if path.isfile(fileDir):
											file = Image.open(fileDir).convert("RGBA").resize((int(item["w"]*m), int(item["h"]*m)), Image.NEAREST)
											img.paste(file, (int(item["x"]*m), int(item["y"]*m)))
									newDirectory = path.dirname(spritesheetTexture)
									if not path.exists(newDirectory):
										makedirs(newDirectory)
									img.save(spritesheetTexture)
									print(f"Created {spritesheetTexture}")
					if "edit" in data["editing"]:
						for textureFile in data["editing"]["edit"]:
							texture = path.join(outputDirectory, textureFile)
							if path.isfile(texture):
								img = Image.open(texture).convert("RGBA")
								if upgrade == True:
									if img.size[0] // data["editing"]["edit"][textureFile]["beforeSize"]["w"] == img.size[1] // data["editing"]["edit"][textureFile]["beforeSize"]["h"]:
										m = img.size[1] / data["editing"]["edit"][textureFile]["beforeSize"]["h"]
										imgNew = Image.new("RGBA", (int(data["editing"]["edit"][textureFile]["afterSize"]["w"]*m), int(data["editing"]["edit"][textureFile]["afterSize"]["h"]*m)))
										if "baseImage" in data["editing"]["edit"][textureFile]:
											baseImg = Image.open(BytesIO(b64decode(data["editing"]["edit"][textureFile]["baseImage"]))).convert("RGBA").resize((int(data["editing"]["edit"][textureFile]["afterSize"]["w"]*m), int(data["editing"]["edit"][textureFile]["afterSize"]["h"]*m)), Image.NEAREST)
											imgNew.paste(baseImg, (0, 0))
										for edit in data["editing"]["edit"][textureFile]["edits"]:
											imgTemp = img.crop((int(edit["oldLocation"]["x"]*m), int(edit["oldLocation"]["y"]*m), int(edit["oldLocation"]["x"]*m)+int(edit["w"]*m), int(edit["oldLocation"]["y"]*m)+int(edit["h"]*m)))
											if "flip" in edit and edit["flip"] == True:
												imgTemp = ImageOps.mirror(imgTemp)
											imgNew.paste(imgTemp, (int(edit["newLocation"]["x"]*m), int(edit["newLocation"]["y"]*m)))
										imgNew.save(texture)
										print(f"Edited {texture}")
								else:
									if img.size[0] // data["editing"]["edit"][textureFile]["afterSize"]["w"] == img.size[1] // data["editing"]["edit"][textureFile]["afterSize"]["h"]:
										m = img.size[1] / data["editing"]["edit"][textureFile]["afterSize"]["h"]
										imgNew = Image.new("RGBA", (int(data["editing"]["edit"][textureFile]["beforeSize"]["w"]*m), int(data["editing"]["edit"][textureFile]["beforeSize"]["h"]*m)))
										for edit in data["editing"]["edit"][textureFile]["edits"]:
											imgTemp = img.crop((int(edit["newLocation"]["x"]*m), int(edit["newLocation"]["y"]*m), int(edit["newLocation"]["x"]*m)+int(edit["w"]*m), int(edit["newLocation"]["y"]*m)+int(edit["h"]*m)))
											if "flip" in edit and edit["flip"] == True:
												imgTemp = ImageOps.mirror(imgTemp)
											imgNew.paste(imgTemp, (int(edit["oldLocation"]["x"]*m), int(edit["oldLocation"]["y"]*m)))
										imgNew.save(texture)
										print(f"Edited {texture}")

				if "files" in data:
					if "move" in data["files"]:
						for (oldLocation, newLocation) in data["files"]["move"].items():
							if upgrade == False:
								oldLocation, newLocation = swap(oldLocation, newLocation)
							oldLocation = path.join(outputDirectory, oldLocation)
							newLocation = path.join(outputDirectory, newLocation)
							if path.isfile(oldLocation) and not path.isfile(newLocation):
								newDirectory = path.dirname(newLocation)
								if not path.exists(newDirectory):
									makedirs(newDirectory)
								moveFile(oldLocation, newLocation)
								if not emissiveString == None and path.isfile(f"{oldLocation[:-4]}{emissiveString}.png"):
									moveFile(f"{oldLocation[:-4]}{emissiveString}.png", f"{newLocation[:-4]}{emissiveString}.png")
								if path.isfile(f"{oldLocation}.mcmeta"):
									moveFile(f"{oldLocation}.mcmeta", f"{newLocation}.mcmeta")
					if "copy" in data["files"]:
						for (oldLocation, newLocation) in data["files"]["copy"].items():
							if upgrade == False:
								oldLocation, newLocation = swap(oldLocation, newLocation)
							oldLocation = path.join(outputDirectory, oldLocation)
							newLocation = path.join(outputDirectory, newLocation)
							if path.isfile(oldLocation) and not path.isfile(newLocation):
								newDirectory = path.dirname(newLocation)
								if not path.exists(newDirectory):
									makedirs(newDirectory)
								copyFile(oldLocation, newLocation)
								if not emissiveString == None and path.isfile(f"{oldLocation[:-4]}{emissiveString}.png"):
									copyFile(f"{oldLocation[:-4]}{emissiveString}.png", f"{newLocation[:-4]}{emissiveString}.png")
								if path.isfile(f"{oldLocation}.mcmeta"):
									copyFile(f"{oldLocation}.mcmeta", f"{newLocation}.mcmeta")
					if "split" in data["files"]:
						for file in data["files"]["split"]:
							file = path.join(outputDirectory, file)
							if upgrade == True:
								if path.isfile(file):
									img = Image.open(file).convert("RGBA")
									w, h = img.size
									m = h // w
									for x in range(m):
										newImg = img.crop((0, w*x, w, w*x+w))
										fileName = f"{file[:-4]}_{x:02}.png"
										newImg.save(fileName)
										print(f"Created {fileName}")
								removeFile(file)
								if path.isfile(f"{file}.mcmeta"):
									removeFile(f"{file}.mcmeta")
							else:
								x = 0
								while path.isfile(f"{file[:-4]}_{x:02}.png"):
									x += 1
								if x != 0:
									with Image.open(f"{file[:-4]}_00.png").convert("RGBA") as base:
										w, h = base.size
									newImg = Image.new("RGBA", (w, w*x))
									for y in range(x):
										tempFile = f"{file[:-4]}_{y:02}.png"
										img = Image.open(tempFile).convert("RGBA")
										newImg.paste(img, (0, w*y))
										removeFile(tempFile)
									newImg.save(file)
									print(f"Created {file}")
									with open(f"{file}.mcmeta", "w") as mcmeta:
										mcmeta.write('{\n  "animation": {}\n}')
									print(f"Created {file}.mcmeta")
					if upgrade == True:
						remove = "remove"
					else:
						remove = "new"
					if remove in data["files"]:	
						for file in data["files"][remove]:
							file = path.join(outputDirectory, file)
							if path.isfile(file):
								removeFile(file)
								if not emissiveString == None and path.isfile(f"{file[:-4]}{emissiveString}.png"):
									removeFile(f"{file[:-4]}{emissiveString}.png")
								if path.isfile(f"{file[:-7]}.mcmeta"):
									removeFile(f"{file[:-7]}.mcmeta")

				if upgrade == True:
					outputVersion = f"{outputVersion.split('.')[0]}.{int(outputVersion.split('.')[1])+1}"
					version = f"{str(version).split('.')[0]}.{int(str(version).split('.')[1])+1}"
				else:
					outputVersion = f"{outputVersion.split('.')[0]}.{int(outputVersion.split('.')[1])-1}"
					version = f"{version.split('.')[0]}.{int(version.split('.')[1])-1}"

			folders = list(walk(outputDirectory))[1:]
			folders.sort(key = len)
			folders.reverse()
			for folder in folders:
				if not folder[2]:
					try:
						rmdir(folder[0])
						print(f"Removed empty folder {folder[0]}")
					except:
						continue

		input("\n\n\nFinished conversion\nPress ENTER to quit...")

	def moveFile(dir1, dir2):
		move(dir1, dir2)
		print(f"Moved {dir1}\n\tto {dir2}")

	def copyFile(dir1, dir2):
		copy(dir1, dir2)
		print(f"Copied {dir1}\n\tto {dir2}")

	def removeFile(dir1):
		remove(dir1)
		print(f"Removed {dir1}")

	def swap(item1, item2):
		return item2, item1

	def copyPixels(img, img2, col):
		if img.size != img2.size:
			img = Image.merge("RGBA", [b.resize((max(img.size[0], img2.size[0]), max(img.size[1], img2.size[1])), Image.NEAREST) for b in img.split()])
			img2 = Image.merge("RGBA", [b.resize((max(img.size[0], img2.size[0]), max(img.size[1], img2.size[1])), Image.NEAREST) for b in img2.split()])
		img3 = Image.new("RGBA", img.size)
		pixels = img.getdata()
		pixels2 = img2.getdata()
		pixels3 = []
		for pixel in range(len(pixels)):
			try:
				if pixels2[pixel][3] == 0:
					if pixels[pixel][3] == 0:
						pixels3.append((*pixels[pixel][:3], 0))
					else:
						pixels3.append((*pixels[pixel][:3], col))
				else:
					pixels3.append(pixels2[pixel])
			except:
				img.show()
				img2.show()
				input("Paused...")
		img3.putdata(pixels3)
		return img3

	def holepunch(img, img2):
		if img.size != img2.size:
			img = img.resize((max(img.size[0], img2.size[0]), max(img.size[1], img2.size[1])), Image.NEAREST)
			img2 = img2.resize((max(img.size[0], img2.size[0]), max(img.size[1], img2.size[1])), Image.NEAREST)
		img3 = Image.new("RGBA", img.size)
		pixels = img.getdata()
		pixels2 = img2.getdata()
		pixels3 = []
		for pixel in range(len(pixels)):
			if pixels[pixel][3] == 0:
				pixels3.append(pixels2[pixel])
			else:
				pixels3.append((0, 0, 0, 0))
		img3.putdata(pixels3)
		return img3

	def cleanImage(img, col):
		pixels = img.getdata()
		pixels2 = []
		for pixel in range(len(pixels)):
			if pixels[pixel][3] == 0:
				pixels2.append((col, col, col, 0))
			else:
				pixels2.append(pixels[pixel])
		img.putdata(pixels2)
		return img

	def hue(file, angle):
		pixels = list(file.convert("HSV").getdata())
		img2 = Image.new("HSV", file.size)
		angle = int(angle/360*255)
		x = 0
		y = 0
		for pixel in pixels:
			pixel = ((pixel[0]+angle)%256, pixel[1], pixel[2])
			img2.putpixel((x, y), pixel)
			x += 1
			if x + 1 > file.size[0]:
				x = 0
				y += 1
		file.paste(img2.convert("RGB"), mask = file)
		return file

	def leaves(outputDirectory, upgrade, emissive):
		with open(resource_path("files/mappings.json")) as jsonFile:
			data = load(jsonFile)
		if "leaves" in data:
			if upgrade == False:
				for leaf in data["leaves"]:
					leafDir = path.join(outputDirectory, leaf)
					outputLeafDir = path.join(outputDirectory, f"{leaf[:-4]}_opaque.png")
					if path.isfile(leafDir) and not path.isfile(outputLeafDir):
						img = Image.open(leafDir).convert("RGBA")
						imgNew = Image.new("RGBA", img.size, (44, 44, 44, 255))
						imgNew.paste(img, (0, 0), img)
						imgNew.save(outputLeafDir)
						print(f"Created {outputLeafDir}")
					if emissive != None:
						emissiveLeafDir = path.join(outputDirectory, f"{leaf[:-4]}{emissive}.png")
						emissiveOutputLeafDir = path.join(outputDirectory, f"{leaf[:-4]}_opaque{emissive}.png")
						if path.isfile(emissiveLeafDir) and not path.isfile(emissiveOutputLeafDir):
							copy(emissiveLeafDir, emissiveOutputLeafDir)
							print(f"Created {emissiveOutputLeafDir}")

	def chests(outputDirectory, upgrade, emissiveString):
		with open(resource_path("files/mappings.json")) as jsonFile:
			data = load(jsonFile)
		if "chests" in data:
			if "single" in data["chests"]:
				for chest in data["chests"]["single"]:
					chestDir = path.join(outputDirectory, chest)
					if path.isfile(chestDir):
						singleChest(chestDir)
						if not emissiveString == None and path.isfile(f"{chestDir[:-4]}{emissiveString}.png"):
							singleChest(f"{chestDir[:-4]}{emissiveString}.png")
			if upgrade == True:
				if "doubleUpgrade" in data["chests"]:
					for chest in data["chests"]["doubleUpgrade"]:
						chestDir = path.join(outputDirectory, chest)
						if path.isfile(chestDir):
							doubleChestUpgrade(chestDir, emissiveString)
							if not emissiveString == None and path.isfile(f"{chestDir[:-4]}{emissiveString}.png"):
								doubleChestUpgrade(f"{chestDir[:-4]}{emissiveString}.png", emissiveString)
			else:
				if "doubleDowngrade" in data["chests"]:
					for chest in data["chests"]["doubleDowngrade"]:
						leftChestDir = path.join(outputDirectory, chest)
						rightChestDir = path.join(outputDirectory, data["chests"]["doubleDowngrade"][chest])
						if path.isfile(leftChestDir) and path.isfile(rightChestDir):
							doubleChestDowngrade(leftChestDir, rightChestDir)
							if not emissiveString == None and path.isfile(f"{leftChestDir[:-4]}{emissiveString}.png") and path.isfile(f"{rightChestDir[:-4]}{emissiveString}.png"):
								doubleChestDowngrade(f"{leftChestDir[:-4]}{emissiveString}.png", f"{rightChestDir[:-4]}{emissiveString}.png")

	def singleChest(dir1, returnMode = False):
		img = Image.open(dir1).convert("RGBA")

		width, height = img.size

		dir2 = path.dirname(dir1)
		file = path.basename(dir1).rsplit(".", 1)[0]

		m = height / 64

		lidTop = img.crop((int(14*m), 0, int(28*m), int(14*m)))
		lidTop = ImageOps.flip(lidTop)

		lidBottom = img.crop((int(28*m), 0, int(42*m), int(14*m)))
		lidBottom = ImageOps.flip(lidBottom)

		baseTop = img.crop((int(14*m), int(19*m), int(28*m), int(33*m)))
		baseTop = ImageOps.flip(baseTop)

		baseBottom = img.crop((int(28*m), int(19*m), int(42*m), int(33*m)))
		baseBottom = ImageOps.flip(baseBottom)

		knobTop = img.crop((int(1*m), 0, int(3*m), int(1*m)))
		knobBottom = img.crop((int(3*m), 0, int(5*m), int(1*m)))

		lidEast = img.crop((0, int(14*m), int(14*m), int(19*m)))
		lidEast = lidEast.rotate(180)

		leftLidSides = img.crop((int(14*m), int(14*m), int(56*m), int(19*m)))
		leftLidSides = leftLidSides.rotate(180)

		baseEast = img.crop((0, int(33*m), int(14*m), int(43*m)))
		baseEast = baseEast.rotate(180)

		baseSides = img.crop((int(14*m), int(33*m), int(56*m), int(43*m)))
		baseSides = baseSides.rotate(180)

		knobEast = img.crop((0, int(1*m), int(1*m), int(5*m)))
		knobEast = knobEast.rotate(180)

		knobSides = img.crop((int(1*m), int(1*m), int(6*m), int(5*m)))
		knobSides = knobSides.rotate(180)

		img.paste(lidTop,(int(28*m), 0))
		img.paste(lidBottom,(int(14*m), 0))
		img.paste(baseTop,(int(28*m), int(19*m)))
		img.paste(baseBottom,(int(14*m), int(19*m)))
		img.paste(knobTop,(int(3*m), 0))
		img.paste(knobBottom,(int(1*m), 0))
		img.paste(lidEast,(0, int(14*m)))
		img.paste(leftLidSides,(int(14*m), int(14*m)))
		img.paste(baseEast,(0, int(33*m)))
		img.paste(baseSides,(int(14*m), int(33*m)))
		img.paste(knobEast,(0, int(1*m)))
		img.paste(knobSides,(int(1*m), int(1*m)))

		if returnMode:
			return img

		img.save(f"{dir2}/{file}.png")
		print(f"Edited: {dir2}/{file}.png")

	def doubleChestUpgrade(dir1, emissiveString):
		img = Image.open(dir1).convert("RGBA")

		width, height = img.size

		dir2 = path.dirname(dir1)
		file = path.basename(dir1).rsplit(".", 1)[0].replace("_double", "")

		m = height / 64

		lidTop = img.crop((int(14*m), 0, int(44*m), int(14*m)))
		lidTop = ImageOps.flip(lidTop)

		lidBottom = img.crop((int(44*m), 0, int(74*m), int(14*m)))
		lidBottom = ImageOps.flip(lidBottom)

		baseTop = img.crop((int(14*m), int(19*m), int(44*m), int(33*m)))
		baseTop = ImageOps.flip(baseTop)

		baseBottom = img.crop((int(44*m), int(19*m), int(74*m), int(33*m)))
		baseBottom = ImageOps.flip(baseBottom)

		knobTop = img.crop((int(1*m), 0, int(3*m), int(1*m)))
		knobBottom = img.crop((int(3*m), 0, int(5*m), int(1*m)))

		lidEast = img.crop((0, int(14*m), int(14*m), int(19*m)))
		lidEast = lidEast.rotate(180)

		leftLidSides = img.crop((int(14*m), int(14*m), int(88*m), int(19*m)))
		leftLidSides = leftLidSides.rotate(180)

		baseEast = img.crop((0, int(33*m), int(14*m), int(43*m)))
		baseEast = baseEast.rotate(180)

		baseSides = img.crop((int(14*m), int(33*m), int(88*m), int(43*m)))
		baseSides = baseSides.rotate(180)

		knobEast = img.crop((0, int(1*m), int(1*m), int(5*m)))
		knobEast = knobEast.rotate(180)

		knobSides = img.crop((int(1*m), int(1*m), int(6*m), int(5*m)))
		knobSides = knobSides.rotate(180)

		img.paste(lidTop,(int(44*m), 0))
		img.paste(lidBottom,(int(14*m), 0))
		img.paste(baseTop,(int(44*m), int(19*m)))
		img.paste(baseBottom,(int(14*m), int(19*m)))
		img.paste(knobTop,(int(3*m), 0))
		img.paste(knobBottom,(int(1*m), 0))
		img.paste(lidEast,(0, int(14*m)))
		img.paste(leftLidSides,(int(14*m), int(14*m)))
		img.paste(baseEast,(0, int(33*m)))
		img.paste(baseSides,(int(14*m), int(33*m)))
		img.paste(knobEast,(0, int(1*m)))
		img.paste(knobSides,(int(1*m), int(1*m)))

		leftLidTop = img.crop((int(59*m), 0, int(74*m), int(14*m)))
		rightLidTop = img.crop((int(44*m), 0, int(59*m), int(14*m)))

		leftLidBottom = img.crop((int(29*m), 0, int(44*m), int(14*m)))
		rightLidBottom = img.crop((int(14*m), 0, int(29*m), int(14*m)))

		leftBaseTop = img.crop((int(59*m), int(19*m), int(74*m), int(33*m)))
		rightBaseTop = img.crop((int(44*m), int(19*m), int(59*m), int(33*m)))

		leftBaseBottom = img.crop((int(29*m), int(19*m), int(44*m), int(33*m)))
		rightBaseBottom = img.crop((int(14*m), int(19*m), int(29*m), int(33*m)))

		leftKnobTop = img.crop((int(2*m), 0, int(3*m), int(1*m)))
		rightKnobTop = img.crop((int(1*m), 0, int(2*m), int(1*m)))

		leftKnobBottom = img.crop((int(4*m), 0, int(5*m), int(1*m)))
		rightKnobBottom = img.crop((int(3*m), 0, int(4*m), int(1*m)))

		leftLidSides = img.crop((int(29*m), int(14*m), int(73*m), int(19*m)))
		rightLidFront = img.crop((int(73*m), int(14*m), int(88*m), int(19*m)))
		rightLidSides = img.crop((0, int(14*m), int(29*m), int(19*m)))

		leftBaseSides = img.crop((int(29*m), int(33*m), int(73*m), int(43*m)))
		rightBaseFront = img.crop((int(73*m), int(33*m), int(88*m), int(43*m)))
		rightBaseSides = img.crop((0, int(33*m), int(29*m), int(43*m)))

		leftKnobSides = img.crop((int(2*m), int(1*m), int(5*m), int(5*m)))
		rightKnobFront = img.crop((int(5*m), int(1*m), int(6*m), int(5*m)))
		rightKnobSides = img.crop((0, int(1*m), int(2*m), int(5*m)))

		leftImg = Image.new("RGBA", (int(64*m), int(64*m)), (0, 0, 0, 0))

		leftImg.paste(leftLidTop,(int(29*m), 0))
		leftImg.paste(leftLidBottom,(int(14*m), 0))
		leftImg.paste(leftBaseTop,(int(29*m), int(19*m)))
		leftImg.paste(leftBaseBottom,(int(14*m), int(19*m)))
		leftImg.paste(leftLidSides,(int(14*m), int(14*m)))
		leftImg.paste(leftBaseSides,(int(14*m), int(33*m)))
		leftImg.paste(leftKnobTop,(int(1*m), 0))
		leftImg.paste(leftKnobBottom,(int(2*m), 0))
		leftImg.paste(leftKnobSides,(int(1*m), int(1*m)))

		rightImg = Image.new("RGBA", (int(64*m), int(64*m)), (0, 0, 0, 0))

		rightImg.paste(rightLidTop,(int(29*m), 0))
		rightImg.paste(rightLidBottom,(int(14*m), 0))
		rightImg.paste(rightBaseTop,(int(29*m), int(19*m)))
		rightImg.paste(rightBaseBottom,(int(14*m), int(19*m)))
		rightImg.paste(rightLidSides,(0, int(14*m)))
		rightImg.paste(rightLidFront,(int(43*m), int(14*m)))
		rightImg.paste(rightBaseSides,(0, int(33*m)))
		rightImg.paste(rightBaseFront,(int(43*m), int(33*m)))
		rightImg.paste(rightKnobTop,(int(1*m), 0))
		rightImg.paste(rightKnobBottom,(int(2*m), 0))
		rightImg.paste(rightKnobSides,(0, int(1*m)))
		rightImg.paste(rightKnobFront,(int(3*m), int(1*m)))

		if not emissiveString == None and file.endswith(emissiveString):
			leftFile = f"{dir2}/{file[:-len(emissiveString)]}_left{emissiveString}.png"
			rightFile = f"{dir2}/{file[:-len(emissiveString)]}_right{emissiveString}.png"
		else:
			leftFile = f"{dir2}/{file}_left.png"
			rightFile = f"{dir2}/{file}_right.png"
		leftImg.save(leftFile)
		rightImg.save(rightFile)
		print(f"Created: {leftFile}\nCreated: {rightFile}")

	def doubleChestDowngrade(leftChestDir, rightChestDir, returnMode = False):
		leftChest = Image.open(leftChestDir).convert("RGBA")
		rightChest = Image.open(rightChestDir).convert("RGBA")

		width, height = leftChest.size

		m = height / 64

		img = Image.new("RGBA", (int(128*m), int(64*m)))

		leftLidBottom = leftChest.crop((int(14*m), 0, int(29*m), int(14*m)))
		leftLidBottom = ImageOps.flip(leftLidBottom)
		img.paste(leftLidBottom, (int(59*m), 0))

		rightLidBottom = rightChest.crop((int(14*m), 0, int(29*m), int(14*m)))
		rightLidBottom = ImageOps.flip(rightLidBottom)
		img.paste(rightLidBottom, (int(44*m), 0))

		leftLidTop = leftChest.crop((int(29*m), 0, int(44*m), int(14*m)))
		leftLidTop = ImageOps.flip(leftLidTop)
		img.paste(leftLidTop, (int(29*m), 0))

		rightLidTop = rightChest.crop((int(29*m), 0, int(44*m), int(14*m)))
		rightLidTop = ImageOps.flip(rightLidTop)
		img.paste(rightLidTop, (int(14*m), 0))

		leftKnobTop = leftChest.crop((int(1*m), 0, int(2*m), int(1*m)))
		leftKnobTop = ImageOps.flip(leftKnobTop)
		img.paste(leftKnobTop, (int(4*m), 0))

		rightKnobTop = leftChest.crop((int(2*m), 0, int(3*m), int(1*m)))
		rightKnobTop = ImageOps.flip(rightKnobTop)
		img.paste(rightKnobTop, (int(2*m), 0))

		leftKnobTop = rightChest.crop((int(1*m), 0, int(2*m), int(1*m)))
		leftKnobTop = ImageOps.flip(leftKnobTop)
		img.paste(leftKnobTop, (int(3*m), 0))

		rightKnobTop = rightChest.crop((int(2*m), 0, int(3*m), int(1*m)))
		rightKnobTop = ImageOps.flip(rightKnobTop)
		img.paste(rightKnobTop, (int(1*m), 0))

		leftBaseBottom = leftChest.crop((int(14*m), int(19*m), int(29*m), int(33*m)))
		leftBaseBottom = ImageOps.flip(leftBaseBottom)
		img.paste(leftBaseBottom, (int(59*m), int(19*m)))

		rightBaseBottom = rightChest.crop((int(14*m), int(19*m), int(29*m), int(33*m)))
		rightBaseBottom = ImageOps.flip(rightBaseBottom)
		img.paste(rightBaseBottom, (int(44*m), int(19*m)))

		leftBaseTop = leftChest.crop((int(29*m), int(19*m), int(44*m), int(33*m)))
		leftBaseTop = ImageOps.flip(leftBaseTop)
		img.paste(leftBaseTop, (int(29*m), int(19*m)))

		rightBaseTop = rightChest.crop((int(29*m), int(19*m), int(44*m), int(33*m)))
		rightBaseTop = ImageOps.flip(rightBaseTop)
		img.paste(rightBaseTop, (int(14*m), int(19*m)))

		leftLidSides = leftChest.crop((int(14*m), int(14*m), int(58*m), int(19*m)))
		leftLidSides = leftLidSides.rotate(180)
		img.paste(leftLidSides, (int(29*m), int(14*m)))

		rightLidEast = rightChest.crop((0, int(14*m), int(14*m), int(19*m)))
		rightLidEast = rightLidEast.rotate(180)
		img.paste(rightLidEast, (0, int(14*m)))

		rightLidFront = rightChest.crop((int(14*m), int(14*m), int(29*m), int(19*m)))
		rightLidFront = rightLidFront.rotate(180)
		img.paste(rightLidFront, (int(73*m), int(14*m)))

		rightLidWest = rightChest.crop((int(43*m), int(14*m), int(58*m), int(19*m)))
		rightLidWest = rightLidWest.rotate(180)
		img.paste(rightLidWest, (int(14*m), int(14*m)))

		leftBaseSides = leftChest.crop((int(14*m), int(33*m), int(58*m), int(43*m)))
		leftBaseSides = leftBaseSides.rotate(180)
		img.paste(leftBaseSides, (int(29*m), int(33*m)))

		rightBaseEast = rightChest.crop((0, int(33*m), int(14*m), int(43*m)))
		rightBaseEast = rightBaseEast.rotate(180)
		img.paste(rightBaseEast, (0, int(33*m)))

		rightBaseWest = rightChest.crop((int(14*m), int(33*m), int(29*m), int(43*m)))
		rightBaseWest = rightBaseWest.rotate(180)
		img.paste(rightBaseWest, (int(73*m), int(33*m)))

		rightBaseFront = rightChest.crop((int(43*m), int(33*m), int(58*m), int(43*m)))
		rightBaseFront = rightBaseFront.rotate(180)
		img.paste(rightBaseFront, (int(14*m), int(33*m)))

		leftKnobSides = leftChest.crop((int(1*m), int(1*m), int(4*m), int(5*m)))
		leftKnobSides = leftKnobSides.rotate(180)
		img.paste(leftKnobSides, (int(2*m), int(1*m)))

		rightKnobEast = rightChest.crop((0, int(1*m), int(1*m), int(5*m)))
		rightKnobEast = rightKnobEast.rotate(180)
		img.paste(rightKnobEast, (0, int(1*m)))

		rightKnobWest = rightChest.crop((int(1*m), int(1*m), int(2*m), int(5*m)))
		rightKnobWest = rightKnobWest.rotate(180)
		img.paste(rightKnobWest, (int(5*m), int(1*m)))

		rightKnobFront = rightChest.crop((int(3*m), int(1*m), int(4*m), int(5*m)))
		rightKnobFront = rightKnobFront.rotate(180)
		img.paste(rightKnobFront, (int(1*m), int(1*m)))

		if returnMode:
			return img

		file = path.basename(leftChestDir).rsplit(".", 1)[0].replace("_left", "_double")

		outFile = path.join(path.dirname(leftChestDir), f"{file}.png")
		img.save(outFile)
		print(f"Created: {outFile}")

	def mojang(outputDirectory, upgrade):
		if upgrade == True:
			file = path.join(outputDirectory, "assets/minecraft/textures/gui/title/mojang.png")
			if path.isfile(file):
				mojangConversion(file, "upgrade")
				colourProperties = path.join(outputDirectory, "assets/minecraft/optifine/color.properties")
				if path.isfile(colourProperties):
					with open(colourProperties) as file:
						if not "screen.loading.blend" in file.read():
							with open(colourProperties, "a") as colour:
								colour.write("\nscreen.loading.blend=off")
								print("Added screen.loading.blend=off to assets/minecraft/optifine/color.properties")
				else:
					newDirectory = path.dirname(colourProperties)
					if not path.exists(newDirectory):
						makedirs(newDirectory)
					with open(colourProperties, "w") as colour:
						colour.write("screen.loading.blend=off")
		else:
			file = path.join(outputDirectory, "assets/minecraft/textures/gui/title/mojangstudios.png")
			if path.isfile(file):
				mojangConversion(file, "downgrade")

	def mojangConversion(dir1, mode):
		img = Image.open(dir1).convert("RGBA")
		dir2 = path.dirname(dir1)
		if mode == "upgrade":
			img = img.crop(img.getbbox())
			if img.size[0] < img.size[1] * 4:
				imgNew = Image.new("RGBA", (img.size[1] * 4 + 16, img.size[1] + 4))
				imgNew.paste(img, ((img.size[1] * 4 - img.size[0]) // 2 + 8, 2))
			elif img.size[0] > img.size[1] * 4:
				imgNew = Image.new("RGBA", (img.size[0] + 16, img.size[0] // 4 + 4))
				imgNew.paste(img, (8, (img.size[1] // 4) // 2 + 2))
			else:
				imgNew = Image.new("RGBA", (img.size[0] + 16, img.size[1] + 4))
				imgNew.paste(img, (8, 2))
			if imgNew.size[0] > 2048:
				imgNew = imgNew.resize((2048, 512), Image.NEAREST)
			imgFinal = Image.new("RGBA", (imgNew.size[0] // 2, imgNew.size[0] // 2))
			imgFinal.paste(imgNew, (0, 0))
			imgFinal.paste(imgNew, (-imgNew.size[0] // 2, imgNew.size[0] // 4))
			imgFinal.save(f"{dir2}/mojangstudios.png")
			print(f"Converted {dir2}/mojang.png\n\tto {dir2}/mojangstudios.png")
		elif mode == "downgrade":
			if img.size[0] != img.size[1]:
				print("Image is not a square. Invalid logo")
				sys.exit()
			imgNew = Image.new("RGBA", (img.size[0] * 2, img.size[0] // 2))
			imgNew.paste(img.crop((0, 0, img.size[0], img.size[1] // 2)))
			imgNew.paste(img.crop((0, img.size[1] // 2, img.size[0], img.size[1])), (img.size[0], 0))
			img = imgNew.crop(imgNew.getbbox())
			imgFinal = Image.new("RGBA", (img.size[0], img.size[0]))
			imgFinal.paste(img, (0, (imgFinal.size[1] - img.size[1]) // 2))
			imgFinal.save(f"{dir2}/mojang.png")
			print(f"Converted {dir2}/mojangstudios.png\n\tto {dir2}/mojang.png")

	def redstone(dir1, upgrade, returnMode = False):
		if upgrade == True:
			overlay = path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_cross_overlay.png")
			line = path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_line.png")
			cross = path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_cross.png")
			if path.isfile(overlay):
				moveFile(overlay, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_overlay.png"))
			if path.isfile(line):
				lineImg = Image.open(line).convert("RGBA")
				lineImg = lineImg.transpose(Image.ROTATE_90)
				lineImg.save(line)
				print(f"Rotated {line}")
				copyFile(line, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_line0.png"))
				moveFile(line, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_line1.png"))
			if path.isfile(cross):
				dot = path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_dot.png")
				moveFile(cross, dot)
				dotImg = Image.open(dot).convert("RGBA")
				dotMiddle = dotImg.crop((dotImg.size[0]//4, dotImg.size[1]//4, (dotImg.size[0]//4)*3, (dotImg.size[1]//4)*3))
				dotNew = Image.new("RGBA", dotImg.size)
				dotNew.paste(dotMiddle, (dotImg.size[0]//4, dotImg.size[1]//4))
				dotNew.save(dot)
				print(f"Edited {dot}")
		else:
			if not returnMode:
				overlay = path.join(dir1, "assets/minecraft/textures/block/redstone_dust_overlay.png")
				if path.isfile(overlay):
					copyFile(overlay, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_cross_overlay.png"))
					moveFile(overlay, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_line_overlay.png"))
			line0 = path.join(dir1, "assets/minecraft/textures/block/redstone_dust_line0.png")
			line1 = path.join(dir1, "assets/minecraft/textures/block/redstone_dust_line1.png")
			dot = path.join(dir1, "assets/minecraft/textures/block/redstone_dust_dot.png")
			if path.isfile(line0):
				linePath = line0
				lineMode = 0
			elif path.isfile(line1):
				linePath = line1
				lineMode = 1
			else:
				linePath = None
			if not linePath == None:
				lineImg = Image.open(linePath).convert("RGBA")
				lineOld = lineImg
				lineImg = lineImg.transpose(Image.ROTATE_270)
				if not returnMode:
					lineImg.save(linePath)
					print(f"Rotated {linePath}")
				if path.isfile(dot):
					dotImg = Image.open(dot).convert("RGBA")
					if lineImg.size[0] > dotImg.size[0]:
						dotImg = dotImg.resize(lineImg.size)
					else:
						lineImg = lineImg.resize(dotImg.size)
						lineOld = lineOld.resize(dotImg.size)
					lineImg = lineImg.convert("RGBA")
					lineOld = lineOld.convert("RGBA")
					lineImg = lineImg.transpose(Image.ROTATE_180)
					dotImg.paste(lineOld, (0, 0), lineOld)
					dotImg.paste(lineImg, (0, 0), lineImg)
					if not returnMode:
						dotImg.save(dot)
						print(f"Edited {dot}")
						moveFile(dot, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_cross.png"))
				else:
					dotImg = None
				if not returnMode:
					moveFile(linePath, path.join(dir1, "assets/minecraft/textures/blocks/redstone_dust_line.png"))
					if lineMode == 0:
						if path.isfile(line1):
							removeFile(line1)
				if returnMode:
					return (lineImg, dotImg)

	def gui7(dir1, upgrade):
		file = path.join(dir1, "assets/minecraft/textures/gui/container/enchanting_table.png")
		if path.isfile(file):
			img = Image.open(file).convert("RGBA")
			m = img.size[0] / 256
			blank = img.crop((int(24*m), int(28*m), int(42*m), int(46*m)))
			if upgrade == True:
				box = img.crop((int(24*m), int(46*m), int(42*m), int(64*m)))
				img.paste(blank, (int(24*m), int(46*m)))
				img.paste(box, (int(14*m), int(46*m)))
				img.paste(box, (int(34*m), int(46*m)))
				textField = img.crop((int(60*m), int(14*m), int(78*m), int(71*m)))
				img.paste(textField, (int(59*m), int(14*m)))
				img.paste(textField, (int(78*m), int(14*m)))
				textField2 = img.crop((int(167*m), int(14*m), int(168*m), int(71*m)))
				img.paste(textField2, (int(77*m), int(14*m)))
			else:
				box = img.crop((int(14*m), int(46*m), int(32*m), int(64*m)))
				img.paste(blank, (int(14*m), int(46*m)))
				img.paste(blank, (int(34*m), int(46*m)))
				img.paste(box, (int(24*m), int(46*m)))
				textField = img.crop((int(78*m), int(14*m), int(98*m), int(71*m)))
				img.paste(textField, (int(59*m), int(14*m)))
			img.save(file)
			print(f"Edited {file}")

	def gui8(dir1, upgrade):
		file = path.join(dir1, "assets/minecraft/textures/gui/container/brewing_stand.png")
		if path.isfile(file):
			img = Image.open(file).convert("RGBA")
			m = img.size[0] / 256
			if upgrade == True:
				bottles = img.crop((int(55*m), int(45*m), int(119*m), int(70*m)))
				pipes = img.crop((int(80*m), int(44*m), int(94*m), int(47*m)))
				blank = img.crop((int(78*m), int(11*m), int(103*m), int(16*m)))
				bubbles = img.crop((int(66*m), int(15*m), int(78*m), int(42*m)))
				box = img.crop((int(7*m), int(83*m), int(25*m), int(101*m)))
				img.paste(bottles, (int(55*m), int(50*m)))
				img.paste(pipes, (int(80*m), int(47*m)))
				img.paste(blank, (int(55*m), int(45*m)))
				img.paste(blank, (int(94*m), int(45*m)))
				img.paste(bubbles, (int(64*m), int(15*m)))
				img.paste(box, (int(16*m), int(16*m)))
			else:
				bottles = img.crop((int(55*m), int(50*m), int(119*m), int(80*m)))
				blank = img.crop((int(119*m), int(16*m), int(158*m), int(48*m)))
				blank2 = img.crop((int(96*m), int(43*m), int(114*m), int(45*m)))
				bubbles = img.crop((int(62*m), int(15*m), int(74*m), int(42*m)))
				img.paste(bottles, (int(55*m), int(45*m)))
				img.paste(blank, (int(16*m), int(16*m)))
				img.paste(blank2, (int(60*m), int(43*m)))
				img.paste(bubbles, (int(64*m), int(15*m)))
			img.save(file)
			print(f"Edited {file}")
		file = path.join(dir1, "assets/minecraft/textures/gui/container/creative_inventory/tab_inventory.png")
		if path.isfile(file):
			img = Image.open(file).convert("RGBA")
			m = img.size[0] / 256
			if upgrade == True:
				ui = img.crop((int(8*m), int(5*m), int(80*m), int(50*m)))
				blank = img.crop((int(80*m), int(5*m), int(125*m), int(50*m)))
				box = img.crop((int(8*m), int(5*m), int(26*m), int(23*m)))
				img.paste(ui, (int(53*m), int(5*m)))
				img.paste(blank, (int(8*m), int(5*m)))
				img.paste(box, (int(34*m), int(19*m)))
			else:
				ui = img.crop((int(53*m), int(5*m), int(125*m), int(50*m)))
				blank = img.crop((int(125*m), int(5*m), int(170*m), int(50*m)))
				img.paste(ui, (int(8*m), int(5*m)))
				img.paste(blank, (int(80*m), int(5*m)))
			img.save(file)
			print(f"Edited {file}")
		file = path.join(dir1, "assets/minecraft/textures/gui/container/inventory.png")
		if path.isfile(file):
			img = Image.open(file).convert("RGBA")
			m = img.size[0] / 256
			if upgrade == True:
				background = img.crop((int(78*m), int(7*m), int(82*m), int(79*m)))
				img.paste(background, (int(75*m), int(7*m)))
				grid = img.crop((int(77*m), int(25*m), int(161*m), int(69*m)))
				box = img.crop((int(143*m), int(35*m), int(161*m), int(53*m)))
				img.paste(grid, (int(87*m), int(17*m)))
				img.paste(box, (int(76*m), int(61*m)))
			else:
				background = img.crop((int(72*m), int(7*m), int(76*m), int(79*m)))
				grid = img.crop((int(97*m), int(9*m), int(171*m), int(53*m)))
				blank = img.crop((int(94*m), int(61*m), int(109*m), int(79*m)))
				blank2 = img.crop((int(161*m), int(9*m), int(171*m), int(27*m)))
				img.paste(background, (int(75*m), int(7*m)))
				img.paste(grid, (int(87*m), int(17*m)))
				img.paste(blank, (int(79*m), int(61*m)))
				img.paste(blank2, (int(161*m), int(27*m)))
			img.save(file)
			print(f"Edited {file}")

	def chestFront(img):
		m = img.size[0] // 64
		flat = Image.new("RGBA", (16*m, 16*m), (255*m, 0, 0, 255*m))
		flat.paste(img.crop((14*m, 33*m, 28*m, 43*m)), (1*m, 5*m))
		flat.paste(img.crop((14*m, 14*m, 28*m, 19*m)), (1*m, 1*m))
		flat.paste(img.crop((1*m, 1*m, 3*m, 5*m)), (7*m, 3*m))
		flat.paste(flat.crop((1*m, 1*m, 15*m, 3*m)), (1*m, 0))
		flat.paste(flat.crop((1*m, 13*m, 15*m, 15*m)), (1*m, 14*m))
		flat.paste(flat.crop((1*m, 0, 3*m, 16*m)))
		flat.paste(flat.crop((13*m, 0, 15*m, 16*m)), (14*m, 0))
		return flat

	def chestSide(img):
		m = img.size[0] // 64
		flat = Image.new("RGBA", (16*m, 16*m), (255*m, 0, 0, 255*m))
		flat.paste(img.crop((0, 33*m, 14*m, 43*m)), (1*m, 5*m))
		flat.paste(img.crop((0, 14*m, 14*m, 19*m)), (1*m, 1*m))
		flat.paste(flat.crop((1*m, 1*m, 15*m, 3*m)), (1*m, 0))
		flat.paste(flat.crop((1*m, 13*m, 15*m, 15*m)), (1*m, 14*m))
		flat.paste(flat.crop((1*m, 0, 3*m, 16*m)))
		flat.paste(flat.crop((13*m, 0, 15*m, 16*m)), (14*m, 0))
		return flat

	def chestTop(img):
		m = img.size[0] // 64
		flat = Image.new("RGBA", (16*m, 16*m), (255*m, 0, 0, 255*m))
		flat.paste(img.crop((14*m, 0, 28*m, 28*m)), (1*m, 1*m))
		flat.paste(flat.crop((1*m, 1*m, 15*m, 3*m)), (1*m, 0))
		flat.paste(flat.crop((1*m, 13*m, 15*m, 15*m)), (1*m, 14*m))
		flat.paste(flat.crop((1*m, 0, 3*m, 16*m)))
		flat.paste(flat.crop((13*m, 0, 15*m, 16*m)), (14*m, 0))
		return flat

	converter()
except Exception as e:
	input(f"-- ERROR --\n\n{e}")