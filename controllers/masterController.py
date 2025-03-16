# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from datetime import datetime, date
import json


class MasterData(http.Controller):

    ## GET Configuraciones
    @http.route("/api/configurations", auth="user", type="json", methods=["GET"])
    def get_configurations(self):
        try:
            # Obtener configuración general
            config = request.env["appwms.config.general"].sudo().search([], limit=1)
            config_data = {"muelle_option": config.muelle_option if config else None}

            # Obtener datos del usuario autenticado
            user = request.env.user
            user_data = {
                "name": user.name,
                "id": user.id,
                "last_name": user.name,
                "email": user.email,
            }

            ## 

            # Verificar permisos en appwms.users_wms
            user_wms = request.env["appwms.users_wms"].sudo().search([("user_id", "=", user.id)], limit=1)
            if not user_wms:
                return {
                    "code": 401,
                    "msg": "El usuario no tiene permisos en el módulo de configuraciones en Odoo",
                }

            user_permissions = request.env["appwms.user_permission_app"].sudo().search([("user_id", "=", user.id)], limit=1)
            if not user_permissions:
                return {
                    "code": 401,
                    "msg": "El usuario no tiene permisos específicos asignados",
                }

            # Construir respuesta final
            response_data = {
                **user_data,
                "rol": user_wms.user_rol if user_wms.user_rol else "USER",
                "muelle_option": config_data.get("muelle_option"),
                "location_picking_manual": user_permissions.location_picking_manual,
                "manual_product_selection": user_permissions.manual_product_selection,
                "manual_quantity": user_permissions.manual_quantity,
                "manual_spring_selection": user_permissions.manual_spring_selection,
                "show_detalles_picking": user_permissions.show_detalles_picking,
                "show_next_locations_in_details": user_permissions.show_next_locations_in_details,
                "location_pack_manual": user_permissions.location_pack_manual,
                "show_detalles_pack": user_permissions.show_detalles_pack,
                "show_next_locations_in_details_pack": user_permissions.show_next_locations_in_details_pack,
                "manual_product_selection_pack": user_permissions.manual_product_selection_pack,
                "manual_quantity_pack": user_permissions.manual_quantity_pack,
                "manual_spring_selection_pack": user_permissions.manual_spring_selection_pack,
                "scan_product": user_permissions.scan_product,
                "allow_move_excess": user_permissions.allow_move_excess,
                "hide_expected_qty": user_permissions.hide_expected_qty,
                "manual_product_reading": user_permissions.manual_product_reading,
                "manual_source_location": user_permissions.manual_source_location,
                "show_owner_field": user_permissions.show_owner_field,
            }

            return {"code": 200, "result": response_data}

        except AccessError as e:
            return {"code": 403, "msg": "Acceso denegado: {}".format(str(e))}
        except Exception as err:
            return {"code": 400, "msg": "Error inesperado: {}".format(str(err))}

            # return {"status": "error", "message": str(e)}

    ## GET Muelles
    @http.route("/api/muelles", auth="user", type="json", methods=["GET"])
    def get_muelles(self):
        try:
            # Obtener todos los muelles con las condiciones especificadas
            muelles = request.env["stock.location"].sudo().search([("usage", "=", "internal"), ("is_a_dock", "=", True)])

            array_muelles = []

            for muelle in muelles:
                array_muelles.append(
                    {
                        "id": muelle.id,
                        "name": muelle.name,
                        "complete_name": muelle.complete_name,
                        "location_id": (muelle.location_id.id if muelle.location_id else None),
                        "barcode": muelle.barcode or "",
                    }
                )

            return {"code": 200, "result": array_muelles}

        except AccessError as e:
            return {"code": 403, "msg": "Acceso denegado: {}".format(str(e))}
        except Exception as err:
            return {"code": 400, "msg": "Error inesperado: {}".format(str(err))}

    ## GET Novedades de Picking
    @http.route("/api/picking_novelties", auth="user", type="json", methods=["GET"])
    def get_picking_novelties(self):
        try:
            # Obtener todas las novedades de picking
            picking_novelties = request.env["picking.novelties"].sudo().search([])

            array_picking_novelties = []

            for novelty in picking_novelties:
                array_picking_novelties.append(
                    {
                        "id": novelty.id,
                        "name": novelty.name,
                        "code": novelty.code,
                    }
                )

            return {"code": 200, "result": array_picking_novelties}

        except AccessError as e:
            return {"code": 403, "msg": "Acceso denegado: {}".format(str(e))}
        except Exception as err:
            return {"code": 400, "msg": "Error inesperado: {}".format(str(err))}

    ## POST Tiempo de inicio de Picking
    @http.route("/api/update_start_time", auth="user", type="json", methods=["POST"])
    def post_picking_start_time(self, picking_id, start_time, field_name):
        try:
            # Buscar el picking
            picking = request.env["stock.picking.batch"].sudo().search([("id", "=", picking_id)], limit=1)

            if not picking:
                return {"code": 404, "msg": "No se encontró el picking con el ID proporcionado"}

            # Validar start_time
            if not start_time:
                return {"code": 400, "msg": "El tiempo 'start_time' es requerido"}

            # Convertir start_time a datetime para validaciones
            try:
                start_time_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return {"code": 400, "msg": "Formato de start_time inválido. Debe ser 'YYYY-MM-DD HH:MM:SS'"}

            # Validar que el start_time no sea en el futuro
            # if start_time_dt > datetime.now():
            #     return {"code": 400, "msg": "start_time no puede ser en el futuro"}

            # Guardar start_time
            picking.sudo().write({field_name: start_time_dt})

            return {"code": 200, "msg": "Tiempo de inicio actualizado correctamente"}

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado {str(err)}"}

    ## POST Tiempo de finalización de Picking
    @http.route("/api/update_end_time", auth="user", type="json", methods=["POST"])
    def post_picking_end_time(self, picking_id, end_time, field_name):
        try:
            # Buscar el picking batch
            picking = request.env["stock.picking.batch"].sudo().search([("id", "=", picking_id)], limit=1)

            if not picking:
                return {"code": 404, "msg": "No se encontró el picking con el ID proporcionado"}

            # Validar end_time
            if not end_time:
                return {"code": 400, "msg": "El tiempo 'end_time' es requerido"}

            # Convertir end_time a datetime
            try:
                end_time_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return {"code": 400, "msg": "Formato de end_time inválido. Debe ser 'YYYY-MM-DD HH:MM:SS'"}

            # Validar que end_time no sea en el futuro
            # if end_time_dt > datetime.now():
            #     return {"code": 400, "msg": "end_time no puede ser en el futuro"}

            # Obtener el nombre del campo de inicio correspondiente
            field_name_start = field_name.replace("end_", "start_")

            # Validar que el campo start_time correspondiente ya esté registrado
            start_time_str = getattr(picking, field_name_start, None)
            if not start_time_str:
                return {"code": 400, "msg": f"No se puede registrar '{field_name}' sin un '{field_name_start}' previo"}

            # Convertir start_time a datetime
            start_time_dt = datetime.strptime(str(start_time_str), "%Y-%m-%d %H:%M:%S")

            # Validar que end_time sea mayor que start_time
            if end_time_dt <= start_time_dt:
                return {"code": 400, "msg": f"'{field_name}' debe ser mayor que '{field_name_start}'"}

            # Guardar end_time
            picking.sudo().write({field_name: end_time_dt})

            return {"code": 200, "msg": f"{field_name} actualizado correctamente"}

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado {str(err)}"}

    ## POST Tiempo de inicio de batch por usuario
    @http.route("/api/start_time_batch_user", auth="user", type="json", methods=["POST"])
    def post_start_time_batch_user(self, **auth):
        try:
            # Validar campos requeridos
            required_fields = ["id_batch", "start_time", "user_id", "operation_type"]
            for field in required_fields:
                if not auth.get(field):
                    return {"code": 400, "msg": f"El campo '{field}' es requerido"}

            batch_id = auth.get("id_batch")
            user_id = auth.get("user_id")
            operation_type = auth.get("operation_type")

            # Buscar el Batch
            batch = request.env["stock.picking.batch"].sudo().search([("id", "=", batch_id)], limit=1)
            if not batch:
                return {"code": 404, "msg": f"No se encontró el BATCH con ID {batch_id}"}

            # Buscar el Usuario
            user = request.env["res.users"].sudo().search([("id", "=", user_id)], limit=1)
            if not user:
                return {"code": 404, "msg": f"No se encontró el usuario con ID {user_id}"}

            # Convertir start_time a datetime
            try:
                start_time = datetime.strptime(auth.get("start_time"), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return {"code": 400, "msg": "Formato de 'start_time' inválido. Debe ser 'YYYY-MM-DD HH:MM:SS'"}

            # Validar que no exista un registro duplicado
            existing_time = (
                request.env["batch.user.time"]
                .sudo()
                .search(
                    [
                        ("batch_id", "=", batch.id),
                        ("user_id", "=", user.id),
                        ("operation_type", "=", operation_type),
                        ("start_time", "!=", False),
                    ],
                    limit=1,
                )
            )

            if existing_time:
                return {"code": 400, "msg": "Ya existe un registro con los mismos datos"}

            # Crear el registro
            new_record = (
                request.env["batch.user.time"]
                .sudo()
                .create(
                    {
                        "batch_id": batch.id,
                        "user_id": user.id,
                        "operation_type": operation_type,
                        "start_time": start_time,
                    }
                )
            )

            return {
                "code": 200,
                "msg": "Registro creado con éxito",
                "data": {
                    "id": new_record.id,
                    "batch_id": new_record.batch_id.id,
                    "user_id": new_record.user_id.id,
                    "operation_type": new_record.operation_type,
                    "start_time": new_record.start_time,
                },
            }

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado: {str(err)}"}

    ## POST Tiempo de fin de batch por usuario
    @http.route("/api/end_time_batch_user", auth="user", type="json", methods=["POST"])
    def post_end_time_batch_user(self, **auth):
        try:
            # Validar campos requeridos
            required_fields = ["id_batch", "end_time", "user_id", "operation_type"]
            for field in required_fields:
                if not auth.get(field):
                    return {"code": 400, "msg": f"El campo '{field}' es requerido"}

            batch_id = auth.get("id_batch")
            user_id = auth.get("user_id")
            operation_type = auth.get("operation_type")

            # Buscar el Batch
            batch = request.env["stock.picking.batch"].sudo().search([("id", "=", batch_id)], limit=1)
            if not batch:
                return {"code": 404, "msg": f"No se encontró el BATCH con ID {batch_id}"}

            # Buscar el Usuario
            user = request.env["res.users"].sudo().search([("id", "=", user_id)], limit=1)
            if not user:
                return {"code": 404, "msg": f"No se encontró el usuario con ID {user_id}"}

            # Convertir end_time a datetime
            try:
                end_time = datetime.strptime(auth.get("end_time"), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return {"code": 400, "msg": "Formato de 'end_time' inválido. Debe ser 'YYYY-MM-DD HH:MM:SS'"}

            # Validar que no exista un registro duplicado
            existing_time = (
                request.env["batch.user.time"]
                .sudo()
                .search(
                    [
                        ("batch_id", "=", batch.id),
                        ("user_id", "=", user.id),
                        ("operation_type", "=", operation_type),
                    ],
                    limit=1,
                )
            )

            if existing_time:
                # actualizar el registro existente
                existing_time.write({"end_time": end_time})
                return {
                    "code": 200,
                    "msg": "Registro actualizado con éxito",
                    "data": {
                        "id": existing_time.id,
                        "batch_id": existing_time.batch_id.id,
                        "user_id": existing_time.user_id.id,
                        "operation_type": existing_time.operation_type,
                        "end_time": existing_time.end_time,
                    },
                }

            else:
                return {"code": 404, "msg": "No se encontró un registro con los datos proporcionados"}

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado: {str(err)}"}

    ## POST Version de la app
    @http.route("/api/create-version", auth="user", type="json", methods=["POST"])
    def post_version(self, **auth):
        try:
            # Validar campos requeridos
            required_fields = ["version"]
            for field in required_fields:
                if not auth.get(field):
                    return {"code": 400, "msg": f"El campo '{field}' es requerido"}

            # Procesar las notas como una lista
            notes = auth.get("notes", [])
            if not isinstance(notes, list):
                notes = ["Sin notas"]

            # Serializar las notas a formato JSON
            notes_json = json.dumps(notes)

            # Crear el registro con la fecha actual
            new_record = (
                request.env["app.version"]
                .sudo()
                .create(
                    {
                        "version": auth.get("version"),
                        "release_date": auth.get("release_date", date.today()),  # Usa la fecha actual si no se envía
                        "notes": notes_json,  # Almacena las notas como JSON
                        "url_download": auth.get("url_download", ""),  # Puede estar vacío
                    }
                )
            )

            # Para la respuesta, devuelve las notas como lista
            return {
                "code": 200,
                "msg": "Registro creado con éxito",
                "data": {
                    "id": new_record.id,
                    "version": new_record.version,
                    "release_date": str(new_record.release_date),
                    "notes": json.loads(new_record.notes),  # Convierte de vuelta a lista
                    "url_download": new_record.url_download,
                },
            }

        except AccessError as e:
            return {"code": 403, "msg": f"Acceso denegado: {str(e)}"}
        except Exception as err:
            return {"code": 400, "msg": f"Error inesperado: {str(err)}"}

    ## GET Versiones de la app
    @http.route("/api/versions", auth="user", type="json", methods=["GET"])
    def get_versions(self):
        try:
            # Obtener todas las versiones
            versions = request.env["app.version"].sudo().search([])

            array_versions = []

            for version in versions:
                array_versions.append(
                    {
                        "id": version.id,
                        "version": version.version,
                        "release_date": str(version.release_date),
                        "notes": version.notes,
                        "url_download": version.url_download,
                    }
                )

            return {"code": 200, "result": array_versions}

        except AccessError as e:
            return {"code": 403, "msg": "Acceso denegado: {}".format(str(e))}
        except Exception as err:
            return {"code": 400, "msg": "Error inesperado: {}".format(str(err))}

    ## GET Ultima version de la app
    @http.route("/api/last-version", auth="user", type="json", methods=["GET"])
    def get_last_version(self):
        try:
            # Obtener la última versión
            last_version = request.env["app.version"].sudo().search([], order="id desc", limit=1)

            if not last_version:
                return {"code": 404, "msg": "No se encontró ninguna versión"}

            # Convertir el texto JSON a una lista Python
            notes_list = []
            if last_version.notes:
                try:
                    notes_list = json.loads(last_version.notes)
                except:
                    notes_list = ["Error al procesar las notas"]

            return {
                "code": 200,
                "result": {
                    "id": last_version.id,
                    "version": last_version.version,
                    "release_date": str(last_version.release_date),
                    "notes": notes_list,  # Ahora devuelve la lista en lugar del string JSON
                    "url_download": last_version.url_download,
                },
            }

        except AccessError as e:
            return {"code": 403, "msg": "Acceso denegado: {}".format(str(e))}
        except Exception as err:
            return {"code": 400, "msg": "Error inesperado: {}".format(str(err))}

    ## Eliminar version de la app
    @http.route("/api/delete-version", auth="user", type="json", methods=["POST"])
    def delete_version(self, version_id):
        try:
            # Buscar la versión
            version = request.env["app.version"].sudo().search([("id", "=", version_id)], limit=1)

            if not version:
                return {"code": 404, "msg": "No se encontró la versión con el ID proporcionado"}

            # Eliminar la versión
            version.unlink()

            return {"code": 200, "msg": "Versión eliminada correctamente"}

        except AccessError as e:
            return {"code": 403, "msg": "Acceso denegado: {}".format(str(e))}
        except Exception as err:
            return {"code": 400, "msg": "Error inesperado: {}".format(str(err))}

    @http.route("/api_app/api_app/objects", auth="public")
    def list(self, **kw):
        return http.request.render(
            "api_app.listing",
            {
                "root": "/api_app/api_app",
                "objects": http.request.env["api_app.api_app"].search([]),
            },
        )

    @http.route('/api_app/api_app/objects/<model("api_app.api_app"):obj>', auth="public")
    def object(self, obj, **kw):
        return http.request.render("api_app.object", {"object": obj})
