import tkinter as tk
from tkinter import messagebox, scrolledtext
from collections import defaultdict
import graphviz
import os
from PIL import Image, ImageTk  # Para manejar imágenes en Tkinter

# --- Funciones del Algoritmo Alpha ---
def generate_relation_matrix(log):
    """Generar la matriz de relaciones a partir del log"""
    # Extrae todos los eventos únicos de las secuencias
    elements = sorted({event for sequence in log for event in sequence})
    
    # Inicializa la matriz con todas las relaciones marcadas como '#L' (sin relación)
    matrix = {a: {b: '#L' for b in elements} for a in elements}
    
    # Identifica las relaciones de sucesión directa en cada secuencia
    direct_successions = set()
    for sequence in log:
        for i in range(len(sequence) - 1):
            direct_successions.add((sequence[i], sequence[i + 1]))
    
    # Actualiza la matriz según las relaciones encontradas
    for a in elements:
        for b in elements:
            if (a, b) in direct_successions:
                if (b, a) in direct_successions:
                    # Si hay relación en ambos sentidos, es paralelismo (∥L)
                    matrix[a][b] = '∥L'
                    matrix[b][a] = '∥L'
                else:
                    # Si solo hay relación en un sentido, es causalidad (→L/←L)
                    matrix[a][b] = '→L'
                    matrix[b][a] = '←L'
    return matrix

def compute_XL_corrected(log):
    """Calcular XL - Pares (A, B) sin filtrar"""
    # Genera la matriz de relaciones base
    relations_matrix = generate_relation_matrix(log)
    elements = sorted({event for sequence in log for event in sequence})
    
    def check_internal_relations(set_elements):
        """Verifica que no haya relaciones de paralelismo o causalidad inversa dentro del conjunto"""
        for i in range(len(set_elements)):
            for j in range(len(set_elements)):
                if i != j and relations_matrix[set_elements[i]][set_elements[j]] != '#L':
                    return False
        return True

    def check_set_relations(set_a, set_b):
        """Verifica que todos los elementos de A estén en relación de causalidad directa con todos los elementos de B"""
        for a in set_a:
            for b in set_b:
                if relations_matrix[a][b] != '→L':
                    return False
        return True

    # Inicializa el conjunto XL
    XL = set()
    n = len(elements)
    
    # Genera todos los posibles subconjuntos no vacíos para A
    for i in range(1, 1 << n):  
        set_a = []
        for j in range(n):
            if i & (1 << j):
                set_a.append(elements[j])
                
        # Verifica que el conjunto A cumple las condiciones
        if not check_internal_relations(set_a):  
            continue
            
        # Genera todos los posibles subconjuntos no vacíos para B
        for k in range(1, 1 << n):  
            set_b = []
            for j in range(n):
                if k & (1 << j):
                    set_b.append(elements[j])
                    
            # Verifica que el conjunto B cumple las condiciones
            if not check_internal_relations(set_b):  
                continue
                
            # Verifica la relación causal entre A y B
            if check_set_relations(set_a, set_b):  
                XL.add((frozenset(set_a), frozenset(set_b)))
    
    return XL

def compute_YL(XL):
    """Calcular YL - Encontrar los pares maximales"""
    YL = set()
    for pair1 in XL:
        is_maximal = True
        for pair2 in XL:
            if pair1 != pair2:
                A1, B1 = pair1
                A2, B2 = pair2
                # Verifica si pair1 es subconjunto de pair2
                if A1.issubset(A2) and B1.issubset(B2) and (len(A2) > len(A1) or len(B2) > len(B1)):
                    is_maximal = False
                    break
        if is_maximal:
            YL.add(pair1)
    return YL

def compute_PL(YL, TI, TO):
    """Calcular PL - Construir el conjunto de lugares"""
    PL = set()
    # Crea lugares para cada par maximal (A,B)
    for A, B in YL:
        place_name = f"p_{','.join(sorted(A))}_{','.join(sorted(B))}"
        PL.add(place_name)
    
    # Añade lugares inicial y final
    PL.add('iL')
    PL.add('oL')
    return PL

def compute_FL(YL, TI, TO):
    """Calcular FL - Construir el conjunto de arcos"""
    FL = set()
    
    # Conecta transiciones con sus lugares correspondientes
    for A, B in YL:
        place_name = f"p_{','.join(sorted(A))}_{','.join(sorted(B))}"
        for a in A:
            FL.add((a, place_name))
        for b in B:
            FL.add((place_name, b))
    
    # Conecta el lugar inicial con las transiciones iniciales
    for t in TI:
        FL.add(('iL', t))
    
    # Conecta las transiciones finales con el lugar final
    for t in TO:
        FL.add((t, 'oL'))
    
    return FL

def visualize_petri_net(PL, TL, FL):
    """Crear visualización de la red de Petri usando Graphviz"""
    # Configura el PATH para Graphviz
    os.environ["PATH"] += os.pathsep + 'C:\\Program Files\\Graphviz\\bin'
    
    # Crea el grafo dirigido
    dot = graphviz.Digraph(comment='Red de Petri')
    dot.attr(rankdir='LR')
    
    # Función auxiliar para formatear nombres de nodos
    def add_parentheses(s):
        """Añade paréntesis solo a las letras individuales"""
        result = []
        for char in s:
            if char.isalpha():
                result.append(f'({char})')
            else:
                result.append(char)
        return ''.join(result)
    
    # Añade lugares (círculos) con estilos específicos
    for p in PL:
        if p == 'iL':
            dot.node(p, 'iL', shape='circle', style='filled', fillcolor='gray')
        elif p == 'oL':
            dot.node(p, 'oL', shape='circle', style='filled', fillcolor='gray')
        else:
            dot.node(p, p, shape='circle')
    
    # Añade transiciones (rectángulos)
    for t in TL:
        dot.node(t, t, shape='box')
    
    # Añade arcos entre nodos
    for f in FL:
        dot.edge(str(f[0]), str(f[1]))
    
    # Genera la imagen
    dot.render('temp_petri_net', format='png', cleanup=True)
    return 'temp_petri_net.png'

def mostrar_grafica_en_ventana(image_path):
    """Muestra la imagen de la red de Petri en una ventana separada"""
    # Crea una nueva ventana
    ventana_grafica = tk.Toplevel()
    ventana_grafica.title("Red de Petri - Paso 8")
    
    # Carga y muestra la imagen
    img = Image.open(image_path)
    img = ImageTk.PhotoImage(img)
    label_imagen = tk.Label(ventana_grafica, image=img)
    label_imagen.image = img  # Evita que la imagen sea recolectada
    label_imagen.pack()

def classify_relations(log):
    """Clasificar las relaciones en el log"""
    # Inicializa diccionario para almacenar diferentes tipos de relaciones
    relations = {
        'sucesiones_directas': set(),
        'causalidades': set(),
        'paralelismo': set(),
        'decisiones': set()
    }
    
    # Identifica sucesiones directas en cada secuencia
    for relation in log:
        for i in range(len(relation) - 1):
            relations['sucesiones_directas'].add((relation[i], '>', relation[i + 1]))
    
    # Identifica relaciones de causalidad y paralelismo
    for relation in log:
        for i in range(len(relation) - 1):
            if (relation[i + 1], relation[i]) not in relations['sucesiones_directas']:
                forward_relation = (relation[i], relation[i + 1])
                inverse_relation = (relation[i + 1], relation[i])
                if inverse_relation in relations['causalidades']:
                    relations['paralelismo'].add(forward_relation)
                    relations['paralelismo'].add(inverse_relation)
                    relations['causalidades'].remove(inverse_relation)
                else:
                    relations['causalidades'].add(forward_relation)
    
    # Identifica relaciones de decisión
    all_letters = set()
    for relation in log:
        all_letters.update(relation)
    all_letters = sorted(all_letters)
    
    for letter in all_letters:
        for other_letter in all_letters:
            if letter != other_letter:
                decision = (letter, '#', other_letter)
                if (letter, '>', other_letter) not in relations['sucesiones_directas'] and \
                   (other_letter, '>', letter) not in relations['sucesiones_directas']:
                    relations['decisiones'].add(decision)
    
    # Añade relaciones de decisión para cada letra consigo misma
    for letter in all_letters:
        relations['decisiones'].add((letter, '#', letter))
    
    return relations

def generate_table(sucesiones_directas, causalidades, paralelismo, decisiones):
    """Generar la tabla de relaciones"""
    # Extrae y ordena todos los elementos únicos
    elementos = set()
    for sucesion in sucesiones_directas:
        elementos.update(sucesion)
    elementos = sorted(elementos)
    
    # Crea la tabla vacía con dimensiones apropiadas
    tabla = [['' for _ in range(len(elementos) + 1)] for _ in range(len(elementos) + 1)]
    
    # Añade encabezados
    for i, elemento in enumerate(elementos):
        tabla[0][i + 1] = elemento
        tabla[i + 1][0] = elemento
    
    # Llena la tabla con las relaciones
    for causalidad in causalidades:
        tabla[elementos.index(causalidad[0]) + 1][elementos.index(causalidad[1]) + 1] = '→L'
        tabla[elementos.index(causalidad[1]) + 1][elementos.index(causalidad[0]) + 1] = '←L'
    
    for paralelo in paralelismo:
        tabla[elementos.index(paralelo[0]) + 1][elementos.index(paralelo[1]) + 1] = '∥L'
        tabla[elementos.index(paralelo[1]) + 1][elementos.index(paralelo[0]) + 1] = '∥L'
    
    for decision in decisiones:
        tabla[elementos.index(decision[0]) + 1][elementos.index(decision[2]) + 1] = '#L'
    
    return tabla

def mostrar_tabla_relaciones(log):
    """Mostrar la tabla de relaciones en formato de texto"""
    # Clasifica las relaciones
    relations = classify_relations(log)
    
    # Genera la tabla
    tabla = generate_table(relations['sucesiones_directas'], 
                         relations['causalidades'],
                         relations['paralelismo'],
                         relations['decisiones'])
    
    # Convierte la tabla a string
    tabla_str = "Tabla de Relaciones:\n"
    for fila in tabla:
        tabla_str += "\t".join(fila) + "\n"
    return tabla_str

# --- Interfaz Gráfica ---
def procesar_input():
    """Procesa la entrada del usuario y genera la red de Petri"""
    # Obtiene la entrada del usuario
    log_input = entry.get()
    try:
        # Parsea la entrada en secuencias
        sequences = log_input.split('>,<')
        log = [sequence.strip('<>').split(',') for sequence in sequences]
        
        # Genera la tabla de relaciones
        tabla_str = mostrar_tabla_relaciones(log)
        
        # Extrae conjuntos necesarios para la red de Petri
        TL = sorted({evento for seq in log for evento in seq})
        TI = {seq[0] for seq in log}
        TO = {seq[-1] for seq in log}
        
        # Aplica el algoritmo Alpha paso a paso
        XL = compute_XL_corrected(log)
        YL = compute_YL(XL)
        PL = compute_PL(YL, TI, TO)
        FL = compute_FL(YL, TI, TO)
        
        # Genera y muestra la visualización
        image_path = visualize_petri_net(PL, TL, FL)
        mostrar_grafica_en_ventana(image_path)
        
        # Prepara el texto con los pasos detallados
        steps = "===== Algoritmo Alpha =====\n\n"
        steps += tabla_str + "\n\n"
        steps += "Paso 1: TL (Conjunto de transiciones):\n" + str(TL) + "\n\n"
        steps += "Paso 2: TI (Transiciones iniciales):\n" + str(TI) + "\n\n"
        steps += "Paso 3: TO (Transiciones finales):\n" + str(TO) + "\n\n"
        steps += "Paso 4: XL (Pares (A, B) sin filtrar):\n"
        for A, B in XL:
            steps += f"({set(A)}, {set(B)})\n"
        steps += "\nPaso 5: YL (Pares maximales):\n"
        for A, B in YL:
            steps += f"({set(A)}, {set(B)})\n"
        steps += "\nPaso 6: PL (Lugares):\n" + str(PL) + "\n\n"
        steps += "Paso 7: FL (Arcos):\n" + str(FL) + "\n\n"
        steps += "Paso 8: α(L) = (PL, TL, FL)\n"
        steps += "Red de Petri resultante:\n"
        steps += f"Lugares (P): {PL}\n"
        steps += f"Transiciones (T): {set(TL)}\n"
        steps += f"Arcos (F): {FL}\n"
        steps += "\nSe ha generado una imagen con la visualización de la red de Petri.\n"
        steps += "\n------------------------------------------------\n\n"
        
        # Actualiza el área de texto con los resultados
        text_box.config(state=tk.NORMAL)
        text_box.delete(1.0, tk.END)
        text_box.insert(tk.END, steps)
        text_box.config(state=tk.DISABLED)
        
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error: {e}")

# --- Configuración de la ventana principal ---
root = tk.Tk()
root.title("Algoritmo Alpha - Pasos 1-8 con Visualización")
root.geometry("800x700")
root.configure(bg='lightblue')

# Crea el label y campo de entrada para los ejercicios
label = tk.Label(root, text="Ingrese los ejercicios (formato <a,b,e,f>,<a,b,e,c,d,b,f>,...):", bg='lightblue')
label.pack(pady=10)

entry = tk.Entry(root, width=80)
entry.pack(pady=10)

# Crea el botón de procesamiento
button = tk.Button(root, text="Procesar", command=procesar_input, bg='lightgreen')
button.pack(pady=10)

# Crea el área de texto para mostrar resultados
text_box = scrolledtext.ScrolledText(root, width=90, height=25, wrap=tk.WORD)
text_box.pack(pady=10)
text_box.config(state=tk.DISABLED)

root.mainloop()
