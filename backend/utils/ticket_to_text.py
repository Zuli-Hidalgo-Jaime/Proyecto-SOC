# backend/utils/ticket_to_text.py

def ticket_to_text(ticket: dict) -> str:
    """
    Convierte un ticket en una cadena de texto unificada, incluyendo
    todos los campos relevantes y el contenido OCR de sus adjuntos (si viene).
    """
    base = (
        f"Número de ticket: {ticket.get('TicketNumber', '')}. "
        f"Título: {ticket.get('ShortDescription', '')}. "
        f"Descripción: {ticket.get('Description', '')}. "
        f"Categoría: {ticket.get('Category', '')}. "
        f"Subcategoría: {ticket.get('Subcategory', '')}. "
        f"Prioridad: {ticket.get('Priority', '')}. "
        f"Severidad: {ticket.get('Severity', '')}. "
        f"Impacto: {ticket.get('Impact', '')}. "
        f"Urgencia: {ticket.get('Urgency', '')}. "
        f"Estado: {ticket.get('Status', '')}. "
        f"Canal: {ticket.get('Channel', '')}. "
        f"Grupo asignado: {ticket.get('AssignmentGroup', '')}. "
        f"Responsable: {ticket.get('AssignedTo', '')}. "
        f"Empresa: {ticket.get('Company', '')}. "
        f"Folio: {ticket.get('Folio', '')}. "
    ).strip()

    ocr_list = ticket.get("attachments_ocr", [])
    ocr_text = "\n".join(ocr_list).strip() if ocr_list else ""

    if ocr_text:
        result = f"{base}\n\nContenido extraído de archivos adjuntos:\n{ocr_text}"
    else:
        result = base

    # 👇 Este print te muestra lo que se embebe cada vez:
    print("\n=============================")
    print("EMBEDDING DEL TICKET:")
    print(result)
    print("=============================\n")

    return result


