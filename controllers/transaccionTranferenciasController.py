from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from datetime import datetime, timedelta
import pytz


class TransaccionTransferenciasController(http.Controller):

    # GET obtener todas las transferencias internas
    @http.route("/api/transferencias", auth="user", type="json", methods=["GET"])
    def get_transferencias(self):
        try:
            user = request.env.user

            # ✅ Validar usuario
            if not user:
                return {"code": 400, "msg": "Usuario no encontrado"}

            array_transferencias = []

            # ✅ Verificar si el usuario tiene almacenes permitidos
            allowed_warehouses = user.allowed_warehouse_ids
            if not allowed_warehouses:
                return {"code": 400, "msg": "El usuario no tiene acceso a ningún almacén"}

            # ✅ Obtener transferencias pendientes directamente de los almacenes permitidos
            for warehouse in allowed_warehouses:
                # Buscar todas las transferencias pendientes (no completadas ni canceladas) para este almacén
                transferencias_pendientes = (
                    request.env["stock.picking"]
                    .sudo()
                    .search(
                        [
                            ("state", "=", "assigned"),
                            ("picking_type_code", "=", "internal"),  # Transferencia interna
                            ("picking_type_id.warehouse_id", "=", warehouse.id),
                            ("sequence_code", "=", "INT"),  # Transferencia interna
                            "|",  # <- OR lógico para incluir ambos casos
                            ("user_id", "=", user.id),  # Transferencias asignadas al usuario actual
                            ("user_id", "=", False),  # Transferencias sin responsable asignado
                        ]
                    )
                )

                for picking in transferencias_pendientes:
                    # Verificar si hay movimientos pendientes - CORREGIDO AQUÍ
                    movimientos_pendientes = picking.move_lines.mapped("move_line_ids").filtered(lambda ml: ml.state == "assigned")

                    # Si no hay movimientos pendientes, omitir esta transferencia
                    if not movimientos_pendientes:
                        continue

                    # Calcular peso total
                    peso_total = sum(move.product_id.weight * move.qty_done for move in movimientos_pendientes if move.product_id.weight)

                    # Calcular número de ítems (suma total de cantidades)
                    numero_items = sum(move.qty_done for move in movimientos_pendientes)

                    transferencia_info = {
                        "id": picking.id,
                        "name": picking.name,  # Nombre de la transferencia
                        "fecha_creacion": picking.create_date,  # Fecha con hora
                        "location_id": picking.location_id.id,
                        "location_name": picking.location_id.display_name,  # Ubicación origen
                        "location_dest_id": picking.location_dest_id.id,
                        "location_dest_name": picking.location_dest_id.display_name,  # Ubicación destino
                        "numero_transferencia": picking.name,  # Número de transferencia
                        "peso_total": peso_total,  # Peso total
                        "numero_lineas": len(movimientos_pendientes),  # Número de líneas (productos)
                        "numero_items": numero_items,  # Número de ítems (cantidades)
                        "state": picking.state,
                        "origin": picking.origin or "",
                        "priority": picking.priority,
                        "warehouse_id": warehouse.id,
                        "warehouse_name": warehouse.name,
                        "responsable_id": picking.user_id.id or 0,
                        "responsable": picking.user_id.name or "",
                        "picking_type": picking.picking_type_id.name,
                        "lineas_transferencia": [],  # Líneas pendientes (is_done_item = False)
                        "lineas_transferencia_enviadas": [],  # Líneas procesadas (is_done_item = True)
                    }

                    # ✅ Procesar las líneas de movimiento
                    for move_line in movimientos_pendientes:
                        product = move_line.product_id

                        # Obtener códigos de barras adicionales
                        array_barcodes = []
                        if "barcode_ids" in product.fields_get():
                            array_barcodes = [
                                {
                                    "barcode": barcode.name,
                                    "id_move": move_line.move_id.id,
                                    "id_product": product.id,
                                    "batch_id": picking.id,
                                }
                                for barcode in product.barcode_ids
                                if barcode.name
                            ]

                        # Obtener empaques del producto
                        array_packing = []
                        if "packaging_ids" in product.fields_get():
                            array_packing = [
                                {
                                    "barcode": pack.barcode,
                                    "cantidad": pack.qty,
                                    "id_move": move_line.move_id.id,
                                    "id_product": product.id,
                                    "batch_id": picking.id,
                                }
                                for pack in product.packaging_ids
                                if pack.barcode
                            ]

                        # Generar la información base común para todas las líneas
                        linea_info = {
                            "id": move_line.id,
                            "id_move": move_line.move_id.id,
                            "id_transferencia": picking.id,
                            "product_id": product.id,
                            "product_name": product.name,
                            "product_code": product.default_code or "",
                            "product_barcode": product.barcode or "",
                            "product_tracking": product.tracking or "",
                            "dias_vencimiento": product.expiration_time or "",
                            "other_barcodes": array_barcodes,
                            "product_packing": array_packing,
                            "quantity_ordered": move_line.move_id.product_qty,
                            "quantity_to_transfer": move_line.product_qty,
                            "quantity_done": move_line.qty_done,
                            "uom": move_line.product_uom_id.name if move_line.product_uom_id else "UND",
                            "location_dest_id": move_line.location_dest_id.id or 0,
                            "location_dest_name": move_line.location_dest_id.display_name or "",
                            "location_dest_barcode": move_line.location_dest_id.barcode or "",
                            "location_id": move_line.location_id.id or 0,
                            "location_name": move_line.location_id.display_name or "",
                            "location_barcode": move_line.location_id.barcode or "",
                            "weight": product.weight or 0,
                        }

                        # Añadir información específica del lote
                        if move_line.lot_id:
                            linea_info.update(
                                {
                                    "lot_id": move_line.lot_id.id,
                                    "lot_name": move_line.lot_id.name,
                                    "fecha_vencimiento": move_line.lot_id.expiration_date or "",
                                }
                            )
                        else:
                            linea_info.update(
                                {
                                    "lot_id": 0,
                                    "lot_name": "",
                                    "fecha_vencimiento": "",
                                }
                            )

                        # Determinar a qué lista añadir la línea según is_done_item
                        if hasattr(move_line, "is_done_item") and move_line.is_done_item:
                            transferencia_info["lineas_transferencia_enviadas"].append(linea_info)
                        else:
                            transferencia_info["lineas_transferencia"].append(linea_info)

                    array_transferencias.append(transferencia_info)

            return {"code": 200, "result": array_transferencias}

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado: {str(err)}"}

    ## GET Obtener tranferencia por id
    @http.route("/api/transferencias/<int:id>", auth="user", type="json", methods=["GET"])
    def get_transferencia_by_id(self, id):
        try:
            user = request.env.user

            # ✅ Validar usuario
            if not user:
                return {"code": 400, "msg": "Usuario no encontrado"}

            # ✅ Buscar la transferencia por ID
            transferencia = request.env["stock.picking"].sudo().search([("id", "=", id)])

            # ✅ Verificar si la transferencia existe
            if not transferencia:
                return {"code": 404, "msg": "Transferencia no encontrada"}

            # ✅ Verificar si el usuario tiene acceso al almacén de esta transferencia
            warehouse = transferencia.picking_type_id.warehouse_id
            if warehouse not in user.allowed_warehouse_ids:
                return {"code": 403, "msg": "No tienes permisos para acceder a esta transferencia"}

            # ✅ Verificar si hay movimientos pendientes
            movimientos_pendientes = transferencia.move_lines.mapped("move_line_ids").filtered(lambda ml: ml.state == "assigned")

            # Si no hay movimientos pendientes, devolver mensaje apropiado
            if not movimientos_pendientes:
                return {"code": 404, "msg": "No hay líneas de transferencia pendientes"}

            # Calcular peso total
            peso_total = sum(move.product_id.weight * move.qty_done for move in movimientos_pendientes if move.product_id.weight)

            # Calcular número de ítems (suma total de cantidades)
            numero_items = sum(move.qty_done for move in movimientos_pendientes)

            transferencia_info = {
                "id": transferencia.id,
                "name": transferencia.name,
                "fecha_creacion": transferencia.create_date,
                "location_id": transferencia.location_id.id,
                "location_name": transferencia.location_id.display_name,
                "location_dest_id": transferencia.location_dest_id.id,
                "location_dest_name": transferencia.location_dest_id.display_name,
                "numero_transferencia": transferencia.name,
                "peso_total": peso_total,
                "numero_lineas": len(movimientos_pendientes),
                "numero_items": numero_items,
                "state": transferencia.state,
                "origin": transferencia.origin or "",
                "priority": transferencia.priority,
                "warehouse_id": warehouse.id,
                "warehouse_name": warehouse.name,
                "responsable_id": transferencia.user_id.id or 0,
                "responsable": transferencia.user_id.name or "",
                "picking_type": transferencia.picking_type_id.name,
                "lineas_transferencia": [],
                "lineas_transferencia_enviadas": [],
            }

            # ✅ Procesar las líneas de movimiento
            for move_line in movimientos_pendientes:
                product = move_line.product_id

                # Obtener códigos de barras adicionales
                array_barcodes = []
                if "barcode_ids" in product.fields_get():
                    array_barcodes = [
                        {
                            "barcode": barcode.name,
                            "id_move": move_line.move_id.id,
                            "id_product": product.id,
                            "batch_id": transferencia.id,
                        }
                        for barcode in product.barcode_ids
                        if barcode.name
                    ]

                # Obtener empaques del producto
                array_packing = []
                if "packaging_ids" in product.fields_get():
                    array_packing = [
                        {
                            "barcode": pack.barcode,
                            "cantidad": pack.qty,
                            "id_move": move_line.move_id.id,
                            "id_product": product.id,
                            "batch_id": transferencia.id,
                        }
                        for pack in product.packaging_ids
                        if pack.barcode
                    ]

                # Generar la información de la línea
                linea_info = {
                    "id": move_line.id,
                    "id_move": move_line.move_id.id,
                    "id_transferencia": transferencia.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_code": product.default_code or "",
                    "product_barcode": product.barcode or "",
                    "product_tracking": product.tracking or "",
                    "dias_vencimiento": product.expiration_time or "",
                    "other_barcodes": array_barcodes,
                    "product_packing": array_packing,
                    "quantity_ordered": move_line.move_id.product_qty,
                    "quantity_to_transfer": move_line.product_qty,
                    "quantity_done": move_line.qty_done,
                    "uom": move_line.product_uom_id.name if move_line.product_uom_id else "UND",
                    "location_dest_id": move_line.location_dest_id.id or 0,
                    "location_dest_name": move_line.location_dest_id.display_name or "",
                    "location_dest_barcode": move_line.location_dest_id.barcode or "",
                    "location_id": move_line.location_id.id or 0,
                    "location_name": move_line.location_id.display_name or "",
                    "location_barcode": move_line.location_id.barcode or "",
                    "weight": product.weight or 0,
                }

                # Añadir información específica del lote
                if move_line.lot_id:
                    linea_info.update(
                        {
                            "lot_id": move_line.lot_id.id,
                            "lot_name": move_line.lot_id.name,
                            "fecha_vencimiento": move_line.lot_id.expiration_date or "",
                        }
                    )
                else:
                    linea_info.update(
                        {
                            "lot_id": 0,
                            "lot_name": "",
                            "fecha_vencimiento": "",
                        }
                    )

                # Determinar a qué lista añadir la línea según is_done_item
                if hasattr(move_line, "is_done_item") and move_line.is_done_item:
                    transferencia_info["lineas_transferencia_enviadas"].append(linea_info)
                else:
                    transferencia_info["lineas_transferencia"].append(linea_info)

            return {"code": 200, "result": transferencia_info}

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado: {str(err)}"}

    ## POST enviar transferencia
    # @http.route("/api/send_tranferencia", auth="user", type="json", methods=["POST"], csrf=False)
    # def send_tranferencia(self, **auth):
    #     try:
    #         user = request.env.user

    #         # ✅ Validar usuario
    #         if not user:
    #             return {"code": 400, "msg": "Usuario no encontrado"}

    #         id_transferencia = auth.get("id_transferencia", 0)
    #         list_items = auth.get("list_items", [])

    #         # ✅ Buscar la transferencia por ID
    #         transferencia = request.env["stock.picking"].sudo().search([("id", "=", id_transferencia)])

    #         # ✅ Verificar si la transferencia existe
    #         if not transferencia:
    #             return {"code": 404, "msg": "Transferencia no encontrada"}

    #         array_result = []

    #         for item in list_items:
    #             move_id = item.get("id_move")
    #             product_id = item.get("id_producto")
    #             lote_id = item.get("lote_producto")
    #             ubicacion_destino = item.get("ubicacion_destino")
    #             cantidad = item.get("cantidad_separada")
    #             fecha_transaccion = item.get("fecha_transaccion")
    #             observacion = item.get("observacion")
    #             id_operario = item.get("id_operario")
    #             time_line = item.get("time_line")

    #             # ✅ Buscar el movimiento por ID
    #             move = request.env["stock.move"].sudo().search([("id", "=", move_id)])
