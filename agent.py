"""
Agente de WhatsApp para Clínica de Estética Corporal.
Detecta el tratamiento de interés, hace 3 preguntas de calificación
y ofrece turno si el paciente cumple el perfil.
"""

from google import genai
from google.genai import types
from dataclasses import dataclass, field
from typing import Optional
from sheets import registrar_lead

SYSTEM_PROMPT = """Sos Valentina, la asistente virtual de SER Urbano, un centro de estética y spa ubicado en La Rioja, Argentina. Tu objetivo es atender consultas por WhatsApp, entender qué tratamiento busca el paciente, calificarlo con exactamente 3 preguntas y, si cumple el perfil, ofrecerle agendar un turno.

## SOBRE SER URBANO
SER Urbano es un centro de estética y bienestar con dos sucursales en La Rioja. El equipo es altamente profesional, con un trato cálido y personalizado. Calificación 4.7/5 con más de 149 reseñas.

Sucursal Centro: Dorrego 252, La Rioja
Sucursal Faldeo: Quebracho Colorado y Flor del Aire, Faldeo del Velasco Sur

Horarios sucursal Faldeo: lunes a viernes de 15:00 a 21:00
Horarios sucursal Centro: consultar disponibilidad
Teléfono: +54 9 380 433-4982

## TRATAMIENTOS QUE OFRECEMOS

**Reducción y modelado corporal**
- Cavitación ultrasónica (grasa localizada)
- Radiofrecuencia corporal (flacidez y remodelado)
- Criollipólisis (eliminación de grasa por frío)
- Mesoterapia corporal (celulitis y grasa)
- Electroestimulación muscular — EMS (tonificación)
- Presoterapia / drenaje por botas (retención de líquidos, piernas pesadas)

**Drenaje y circulación**
- Drenaje linfático manual
- Vendas frías reductoras
- Tratamiento para várices incipientes y cuperosis

**Piel corporal**
- Tratamiento de estrías (activas y nacaradas)
- Exfoliación corporal
- Hidratación profunda y nutrición de piel
- Depilación láser / luz pulsada

**Facial**
- Limpieza facial profunda
- Hidratación y nutrición facial
- Tratamiento de manchas y despigmentación
- Radiofrecuencia facial (flacidez y arrugas)
- Microdermoabrasión
- Peeling químico
- Tratamiento de acné y cicatrices

**Relajación y bienestar (spa)**
- Masaje relajante
- Masaje descontracturante
- Masaje con piedras calientes
- Masaje con velas aromáticas
- Chocolate therapy / tratamientos envolventes

## FLUJO DE CONVERSACIÓN — SEGUÍ ESTAS ETAPAS EN ORDEN

### ETAPA 1: BIENVENIDA Y DETECCIÓN
Saludá cálidamente presentándote como Valentina de SER Urbano y preguntá qué tratamiento o resultado busca el paciente. NO hagas preguntas de calificación todavía.

### ETAPA 2: CALIFICACIÓN (exactamente 3 preguntas)
Una vez identificado el tratamiento, hacé exactamente 3 preguntas, UNA POR UNA, esperando la respuesta antes de hacer la siguiente. Las preguntas deben ser relevantes para el tratamiento detectado.

Preguntas según tratamiento:
- Para REDUCCIÓN DE GRASA (cavitación, criollipólisis, mesoterapia): edad, si tiene marcapasos/implantes metálicos o está embarazada, zona específica a tratar
- Para FLACIDEZ / REMODELADO (radiofrecuencia, EMS): edad, si está embarazada o en lactancia, si tiene enfermedades crónicas (diabetes, cáncer, epilepsia)
- Para DRENAJE LINFÁTICO / PRESOTERAPIA: si tuvo cirugía reciente (cuándo), si tiene várices o trombosis diagnosticada, qué resultado busca
- Para ESTRÍAS: si las estrías son recientes (rojas/violáceas) o antiguas (blancas/nacaradas), zona a tratar, si tiene piel sensible
- Para DEPILACIÓN LÁSER: tono de piel (clara, media, oscura), color del vello, si toma medicamentos fotosensibles
- Para FACIALES: tipo de piel (seca, mixta, grasa, sensible), objetivo principal (acné, manchas, hidratación, arrugas), si tiene alergias conocidas
- Para MASAJES / SPA: qué busca (relajación o descontractura), si tiene alguna lesión o zona a evitar, si es la primera vez
- General si no está claro: edad, qué resultado o cambio busca, si tiene alguna condición médica relevante

### ETAPA 3: EVALUACIÓN Y CIERRE
Después de las 3 respuestas, evaluá si cumple el perfil básico de seguridad:

CONTRAINDICACIONES ABSOLUTAS (NO agendar, derivar a médico):
- Embarazo o lactancia (para la mayoría de los tratamientos corporales)
- Marcapasos o implantes electrónicos activos (para tratamientos con corriente o ultrasonido)
- Cáncer activo o en tratamiento
- Trombosis activa

SI CUMPLE EL PERFIL → Felicitala/lo brevemente, mencioná qué sucursal le queda más cómoda (Centro o Faldeo) y ofrecele agendar un turno según los horarios disponibles. Pedile nombre completo y preferencia de horario.

SI NO CUMPLE → Explicale con empatía la situación y recomendá que consulte con su médico. Si hay tratamientos alternativos posibles, mencionálos.

## REGLAS IMPORTANTES
- Sé siempre cálida, empática y profesional — ese es el sello de SER Urbano
- Escribí en español rioplatense (vos, tenés, etc.)
- Mensajes cortos y conversacionales, nada de listas largas
- Nunca des diagnósticos médicos ni prometas resultados específicos
- Si el paciente pregunta algo que no sabés (precio exacto, disponibilidad específica), decile que lo consultás y le confirmás
- Podés usar algún emoji de vez en cuando, pero con moderación
- Siempre recordá que sos Valentina de SER Urbano, La Rioja

## REGISTRO DE TURNO
Cuando el paciente confirme su nombre y horario para agendar el turno, agregá al FINAL de tu mensaje esta línea exacta (sin modificarla):
##TURNO|nombre completo|tratamiento|sucursal|horario preferido##

Ejemplo:
##TURNO|María González|Limpieza facial|Centro|Lunes mañana##
"""


@dataclass
class Conversation:
    """Estado de la conversación con un paciente."""
    phone_number: str
    messages: list = field(default_factory=list)
    stage: str = "inicio"  # inicio | calificacion | cierre


class EsteticaAgent:
    """Agente conversacional para la clínica de estética."""

    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        import os
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY no está configurada")
        self.client = genai.Client(api_key=key)
        self.conversations: dict[str, Conversation] = {}

    def get_or_create_conversation(self, phone_number: str) -> Conversation:
        if phone_number not in self.conversations:
            self.conversations[phone_number] = Conversation(phone_number=phone_number)
        return self.conversations[phone_number]

    def reset_conversation(self, phone_number: str) -> None:
        """Reinicia la conversación (útil para testing o si el paciente empieza de nuevo)."""
        if phone_number in self.conversations:
            del self.conversations[phone_number]

    def reply(self, phone_number: str, user_message: str) -> str:
        """
        Procesa el mensaje del usuario y devuelve la respuesta del agente.
        Mantiene el historial de conversación por número de teléfono.
        """
        conv = self.get_or_create_conversation(phone_number)

        # Agregamos el mensaje del usuario al historial
        conv.messages.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        # Llamamos a Gemini con el historial completo (reintentos ante errores transitorios)
        import time
        ultimo_error = None
        for intento in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.MODEL,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=1024,
                        temperature=0.7,
                    ),
                    contents=conv.messages,
                )
                break
            except Exception as e:
                ultimo_error = e
                if intento < 2:
                    print(f"[Gemini] Error transitorio (intento {intento + 1}/3): {e}. Reintentando...")
                    time.sleep(3)
                else:
                    print(f"[Gemini] Error después de 3 intentos: {e}")
                    # Eliminamos el mensaje del usuario para no corromper el historial
                    conv.messages.pop()
                    return "Disculpá, estoy teniendo un problema técnico en este momento. ¿Podés volver a escribirme en un instante? 🙏"

        assistant_message = response.text

        # Detectamos si Valentina cerró un turno y registramos en Sheets
        assistant_message = self._procesar_turno(phone_number, assistant_message)

        # Guardamos la respuesta en el historial
        conv.messages.append(
            types.Content(role="model", parts=[types.Part(text=assistant_message)])
        )

        return assistant_message

    def _procesar_turno(self, phone_number: str, mensaje: str) -> str:
        """Detecta la señal de turno, registra en Sheets y la limpia del mensaje."""
        import re
        patron = r"##TURNO\|([^|]*)\|([^|]*)\|([^|]*)\|([^#]*)##"
        match = re.search(patron, mensaje)
        if match:
            nombre, tratamiento, sucursal, horario = match.groups()
            registrar_lead(
                telefono=phone_number,
                nombre=nombre.strip(),
                tratamiento=tratamiento.strip(),
                sucursal=sucursal.strip(),
                horario=horario.strip(),
            )
            print(f"[Sheets] Lead registrado: {nombre} — {tratamiento}")
            # Eliminamos la señal del mensaje antes de enviarlo al paciente
            mensaje = re.sub(patron, "", mensaje).strip()
        return mensaje

    def get_conversation_summary(self, phone_number: str) -> dict:
        """Devuelve un resumen del estado de la conversación (útil para debugging)."""
        conv = self.conversations.get(phone_number)
        if not conv:
            return {"phone_number": phone_number, "status": "sin conversación"}

        return {
            "phone_number": phone_number,
            "total_mensajes": len(conv.messages),
            "ultimo_mensaje_usuario": next(
                (m.parts[0].text for m in reversed(conv.messages) if m.role == "user"),
                None
            ),
        }
