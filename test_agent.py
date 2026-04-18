"""
Script para probar el agente en consola sin necesidad de WhatsApp/Twilio.
Simula una conversación completa de principio a fin.
"""

import os
from dotenv import load_dotenv
from agent import EsteticaAgent

load_dotenv()


def test_interactivo():
    """Modo interactivo: escribís los mensajes vos mismo."""
    agent = EsteticaAgent()
    phone = "test_usuario"

    print("=" * 60)
    print("  AGENTE CLÍNICA BELLA FORMA — Modo Test Interactivo")
    print("  Escribí 'salir' para terminar | 'reset' para reiniciar")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("Vos: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nChau!")
            break

        if not user_input:
            continue

        if user_input.lower() == "salir":
            print("Conversación terminada.")
            break

        if user_input.lower() == "reset":
            agent.reset_conversation(phone)
            print("--- Conversación reiniciada ---\n")
            continue

        response = agent.reply(phone, user_input)
        print(f"\nValentina: {response}\n")


def test_automatico():
    """Simula conversaciones predefinidas para verificar el flujo."""
    agent = EsteticaAgent()

    escenarios = [
        {
            "nombre": "Paciente CALIFICADA - Cavitación",
            "mensajes": [
                "Hola, quiero información sobre cavitación",
                "Tengo 32 años",
                "No, no tengo ningún implante ni marcapasos",
                "Quiero reducir la grasa del abdomen",
            ]
        },
        {
            "nombre": "Paciente NO CALIFICADA - Embarazada",
            "mensajes": [
                "Buen día, me interesa la radiofrecuencia para la flacidez",
                "Tengo 28 años",
                "Sí, estoy embarazada de 5 meses",
            ]
        },
        {
            "nombre": "Paciente CALIFICADA - Drenaje linfático",
            "mensajes": [
                "Quisiera hacer drenaje linfático, me operé hace 3 meses",
                "Sí, fue una cesárea, ya me dieron el alta",
                "No tengo várices ni problemas de circulación",
                "Quiero desinflamarme y mejorar la circulación",
            ]
        },
    ]

    for escenario in escenarios:
        phone = f"test_{escenario['nombre'].replace(' ', '_')}"
        print(f"\n{'=' * 60}")
        print(f"  ESCENARIO: {escenario['nombre']}")
        print(f"{'=' * 60}")

        for msg in escenario["mensajes"]:
            print(f"\nPaciente: {msg}")
            response = agent.reply(phone, msg)
            print(f"Valentina: {response}")

        print()


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print("Ejecutando test automático...\n")
        test_automatico()
    else:
        test_interactivo()
