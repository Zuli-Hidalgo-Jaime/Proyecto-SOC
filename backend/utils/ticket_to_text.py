# backend/utils/ticket_to_text.py
"""
Convert ticket dictionary to unified text for embeddings.
"""

def ticket_to_text(ticket: dict) -> str:
    """
    Converts a ticket into a unified text string, including OCR from attachments.
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

    print("\n=============================")
    print("EMBEDDING DEL TICKET:")
    print(result)
    print("=============================\n")

    return result



