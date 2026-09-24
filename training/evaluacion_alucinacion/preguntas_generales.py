"""
Set de 100 preguntas de conocimiento general, SIN relacion con Techo 360,
para medir alucinacion fuera del dominio del fine-tuning.

Cada entrada: (categoria, pregunta, referencia, confianza_evaluador)
  referencia          -- el hecho correcto contra el que se puntua.
  confianza_evaluador -- "alta" si el evaluador (Claude) esta seguro del
                         hecho; "media" si podria haber matices o el dato
                         cambia con el tiempo. Las de confianza "media" se
                         reportan aparte para no puntuar con falsa certeza.
"""

PREGUNTAS = [
    # ---------------- CIENCIA (15) ----------------
    ("ciencia", "¿Cuál es la fórmula química del agua?", "H2O", "alta"),
    ("ciencia", "¿Cuántos planetas tiene el sistema solar?", "8 desde 2006 (Plutón reclasificado)", "alta"),
    ("ciencia", "¿Qué gas absorben las plantas para la fotosíntesis?", "Dióxido de carbono (CO2)", "alta"),
    ("ciencia", "¿Cuál es el elemento químico con símbolo Fe?", "Hierro", "alta"),
    ("ciencia", "¿A qué temperatura hierve el agua a nivel del mar en grados Celsius?", "100 °C", "alta"),
    ("ciencia", "¿Quién formuló la teoría de la relatividad?", "Albert Einstein", "alta"),
    ("ciencia", "¿Cuál es el planeta más grande del sistema solar?", "Júpiter", "alta"),
    ("ciencia", "¿Qué órgano del cuerpo humano produce la insulina?", "El páncreas", "alta"),
    ("ciencia", "¿Cuántos cromosomas tiene una célula humana normal?", "46 (23 pares)", "alta"),
    ("ciencia", "¿Cuál es la velocidad de la luz en el vacío, aproximadamente?", "~299.792.458 m/s (~300.000 km/s)", "alta"),
    ("ciencia", "¿Qué científica descubrió el radio y el polonio?", "Marie Curie", "alta"),
    ("ciencia", "¿Cuál es el metal líquido a temperatura ambiente?", "Mercurio", "alta"),
    ("ciencia", "¿Qué tipo de roca es el granito: ígnea, sedimentaria o metamórfica?", "Ígnea", "alta"),
    ("ciencia", "¿Cuál es la unidad básica de la herencia biológica?", "El gen", "alta"),
    ("ciencia", "¿Qué fuerza mantiene a los planetas en órbita alrededor del Sol?", "La gravedad", "alta"),

    # ---------------- HISTORIA (15) ----------------
    ("historia", "¿En qué año llegó Cristóbal Colón a América?", "1492", "alta"),
    ("historia", "¿En qué año cayó el Muro de Berlín?", "1989", "alta"),
    ("historia", "¿Quién fue el primer presidente de Estados Unidos?", "George Washington", "alta"),
    ("historia", "¿En qué año comenzó la Segunda Guerra Mundial?", "1939", "alta"),
    ("historia", "¿Qué civilización construyó Machu Picchu?", "La civilización inca", "alta"),
    ("historia", "¿Quién fue Simón Bolívar?", "Líder de la independencia de varios países sudamericanos", "alta"),
    ("historia", "¿En qué año se firmó la independencia de Colombia?", "20 de julio de 1810 (grito); independencia consolidada en 1819", "alta"),
    ("historia", "¿Qué imperio construyó el Coliseo de Roma?", "El Imperio Romano", "alta"),
    ("historia", "¿Quién escribió el Manifiesto Comunista junto a Friedrich Engels?", "Karl Marx", "alta"),
    ("historia", "¿En qué año llegó el hombre a la Luna por primera vez?", "1969", "alta"),
    ("historia", "¿Qué revolución comenzó en Francia en 1789?", "La Revolución Francesa", "alta"),
    ("historia", "¿Quién fue Cleopatra?", "Última reina del Egipto ptolemaico", "alta"),
    ("historia", "¿Qué muro dividió Alemania durante la Guerra Fría?", "El Muro de Berlín", "alta"),
    ("historia", "¿En qué siglo ocurrió la Revolución Industrial?", "Siglo XVIII (con continuación en el XIX)", "alta"),
    ("historia", "¿Quién pintó la Capilla Sixtina?", "Miguel Ángel", "alta"),

    # ---------------- GEOGRAFIA Y ACTUALIDAD (15) ----------------
    ("geografia", "¿Cuál es la capital de Francia?", "París", "alta"),
    ("geografia", "¿Cuál es el río más largo del mundo?", "Nilo o Amazonas según el criterio de medición", "media"),
    ("geografia", "¿Cuál es el océano más grande?", "El Pacífico", "alta"),
    ("geografia", "¿En qué continente está Egipto?", "África", "alta"),
    ("geografia", "¿Cuál es la montaña más alta del mundo?", "El Everest", "alta"),
    ("geografia", "¿Cuál es el país más grande del mundo por superficie?", "Rusia", "alta"),
    ("geografia", "¿Cuál es la capital de Japón?", "Tokio", "alta"),
    ("geografia", "¿Qué desierto es el más grande del mundo?", "La Antártida (desierto polar); el Sahara es el mayor cálido", "media"),
    ("geografia", "¿Cuántos continentes hay?", "Depende del modelo: 5, 6 o 7", "media"),
    ("geografia", "¿Qué moneda se usa en Japón?", "El yen", "alta"),
    ("geografia", "¿Cuál es el país con mayor población del mundo?", "India superó a China en 2023", "media"),
    ("geografia", "¿En qué país se encuentra la Torre Eiffel?", "Francia", "alta"),
    ("geografia", "¿Cuál es la capital de Australia?", "Canberra", "alta"),
    ("geografia", "¿Qué mar separa Europa de África?", "El mar Mediterráneo", "alta"),
    ("geografia", "¿Cuál es el lago más grande del mundo?", "El mar Caspio (lago salado)", "alta"),

    # ---------------- MATEMATICAS BASICAS (12) ----------------
    ("matematicas", "¿Cuánto es 15 por 4?", "60", "alta"),
    ("matematicas", "¿Cuánto es la raíz cuadrada de 144?", "12", "alta"),
    ("matematicas", "¿Cuánto es 7 al cuadrado?", "49", "alta"),
    ("matematicas", "¿Cuánto es 250 dividido entre 5?", "50", "alta"),
    ("matematicas", "¿Cuál es el valor aproximado de pi con dos decimales?", "3,14", "alta"),
    ("matematicas", "¿Cuánto es el 20% de 300?", "60", "alta"),
    ("matematicas", "¿Cuántos grados suman los ángulos internos de un triángulo?", "180 grados", "alta"),
    ("matematicas", "¿Cuánto es 1024 dividido entre 2?", "512", "alta"),
    ("matematicas", "Si un producto cuesta 80.000 y tiene 25% de descuento, ¿cuánto cuesta?", "60.000", "alta"),
    ("matematicas", "¿Cuál es el siguiente número primo después de 13?", "17", "alta"),
    ("matematicas", "¿Cuánto es 3 elevado a la 4?", "81", "alta"),
    ("matematicas", "¿Cuántos lados tiene un hexágono?", "6", "alta"),

    # ---------------- CULTURA GENERAL, ARTE Y LITERATURA (15) ----------------
    ("cultura", "¿Quién escribió Cien años de soledad?", "Gabriel García Márquez", "alta"),
    ("cultura", "¿Quién pintó La Mona Lisa?", "Leonardo da Vinci", "alta"),
    ("cultura", "¿Quién escribió Don Quijote de la Mancha?", "Miguel de Cervantes", "alta"),
    ("cultura", "¿Cuántas cuerdas tiene una guitarra clásica?", "6", "alta"),
    ("cultura", "¿Quién compuso la Novena Sinfonía?", "Ludwig van Beethoven", "alta"),
    ("cultura", "¿En qué obra aparece el personaje de Romeo y Julieta?", "Romeo y Julieta, de Shakespeare", "alta"),
    ("cultura", "¿Qué escritor colombiano ganó el Nobel de Literatura?", "Gabriel García Márquez (1982)", "alta"),
    ("cultura", "¿Cuántas notas tiene la escala musical occidental básica?", "7 (do re mi fa sol la si)", "alta"),
    ("cultura", "¿Quién escribió La Odisea?", "Homero", "alta"),
    ("cultura", "¿Qué pintor español pintó el Guernica?", "Pablo Picasso", "alta"),
    ("cultura", "¿Cuál es el idioma más hablado del mundo por número de hablantes nativos?", "Chino mandarín", "media"),
    ("cultura", "¿Quién dirigió la película Titanic de 1997?", "James Cameron", "alta"),
    ("cultura", "¿Qué instrumento tocaba principalmente Louis Armstrong?", "La trompeta", "alta"),
    ("cultura", "¿En qué país nació el escritor Jorge Luis Borges?", "Argentina", "alta"),
    ("cultura", "¿Qué género musical originó Bob Marley principalmente?", "El reggae", "alta"),

    # ---------------- TECNOLOGIA E INFORMATICA (10) ----------------
    ("tecnologia", "¿Qué significa la sigla HTTP?", "HyperText Transfer Protocol", "alta"),
    ("tecnologia", "¿Quién fundó Microsoft junto a Paul Allen?", "Bill Gates", "alta"),
    ("tecnologia", "¿Cuántos bits tiene un byte?", "8", "alta"),
    ("tecnologia", "¿Qué lenguaje de programación creó Guido van Rossum?", "Python", "alta"),
    ("tecnologia", "¿Qué significa CPU?", "Central Processing Unit (unidad central de procesamiento)", "alta"),
    ("tecnologia", "¿Qué empresa desarrolla el sistema operativo Android?", "Google", "alta"),
    ("tecnologia", "¿Qué es un algoritmo, en una frase?", "Secuencia finita de pasos para resolver un problema", "alta"),
    ("tecnologia", "¿Qué significa SQL?", "Structured Query Language", "alta"),
    ("tecnologia", "¿En qué año se fundó Google, aproximadamente?", "1998", "alta"),
    ("tecnologia", "¿Qué protocolo se usa para enviar correo electrónico?", "SMTP", "alta"),

    # ---------------- SALUD Y BIOLOGIA HUMANA (8) ----------------
    ("salud", "¿Cuántos huesos tiene aproximadamente el cuerpo humano adulto?", "206", "alta"),
    ("salud", "¿Qué órgano bombea la sangre?", "El corazón", "alta"),
    ("salud", "¿Cuál es el órgano más grande del cuerpo humano?", "La piel", "alta"),
    ("salud", "¿Qué vitamina se obtiene principalmente del sol?", "La vitamina D", "alta"),
    ("salud", "¿Cuántas cámaras tiene el corazón humano?", "4", "alta"),
    ("salud", "¿Qué célula sanguínea transporta el oxígeno?", "El glóbulo rojo (eritrocito)", "alta"),
    ("salud", "¿Cuál es la temperatura corporal normal aproximada en grados Celsius?", "~37 °C", "alta"),
    ("salud", "¿Qué sistema del cuerpo incluye el cerebro y la médula espinal?", "El sistema nervioso central", "alta"),

    # ---------------- DEPORTES (5) ----------------
    ("deportes", "¿Cada cuántos años se celebran los Juegos Olímpicos de verano?", "Cada 4 años", "alta"),
    ("deportes", "¿Cuántos jugadores tiene un equipo de fútbol en cancha?", "11", "alta"),
    ("deportes", "¿En qué deporte destacó Michael Jordan?", "Baloncesto", "alta"),
    ("deportes", "¿Cuántos jugadores tiene un equipo de voleibol en cancha?", "6", "alta"),
    ("deportes", "¿Qué país ganó el Mundial de fútbol de 2014?", "Alemania", "alta"),

    # ---------------- LENGUA ESPAÑOLA (5) ----------------
    ("lengua", "¿Cuántas letras tiene el alfabeto español actual?", "27", "alta"),
    ("lengua", "¿Qué es un sustantivo, en una frase?", "Palabra que nombra personas, animales, cosas o ideas", "alta"),
    ("lengua", "¿Cuál es el plural de 'crisis'?", "crisis (invariable)", "alta"),
    ("lengua", "¿Qué signo se usa al inicio de una pregunta en español?", "El signo de apertura ¿", "alta"),
    ("lengua", "¿Qué es un sinónimo?", "Palabra con significado igual o muy parecido a otra", "alta"),
]

CATEGORIAS = {}
for cat, *_ in PREGUNTAS:
    CATEGORIAS[cat] = CATEGORIAS.get(cat, 0) + 1

if __name__ == "__main__":
    print(f"Total de preguntas: {len(PREGUNTAS)}")
    print("\nPor categoria:")
    for cat, n in sorted(CATEGORIAS.items(), key=lambda kv: -kv[1]):
        print(f"  {cat:<14}{n:>4}")
    medias = [p for p in PREGUNTAS if p[3] == "media"]
    print(f"\nPreguntas donde el evaluador NO tiene confianza alta: {len(medias)}")
    for cat, preg, ref, _ in medias:
        print(f"  [{cat}] {preg}")
        print(f"      -> {ref}")
