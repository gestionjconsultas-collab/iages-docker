"""
═══════════════════════════════════════════════════════════════════════════════
  ETIQUETAS_POR_TIPO — Perfiles de extracción de documentos administrativos
  ─────────────────────────────────────────────────────────────────────────────
  Cada lista de sinónimos incluye variantes en:
    ES (castellano), CA (catalán), VA (valenciano), EU (euskera), GL (gallego)

  Convención de claves:
    - Nombres de campo en castellano (snake_case)
    - Las listas mezclan todos los idiomas para hacer match directo
    - Si un campo no aplica a un tipo de documento, no se incluye

  Tipos cubiertos:
    1.  provisio_constrenyiment     – Provisió (Ajuntament BCN / ORGT)
    2.  providencia_apremio         – Providencia de apremio (AEAT / estatal)
    3.  providencia_apremio_local   – Providencia apremio ayuntamientos
    4.  embargo_vehiculos           – Embargo vehículos TGSS
    5.  embargo_cuentas             – Embargo cuentas TGSS
    6.  embargo_cuentas_aeat        – Embargo cuentas AEAT
    7.  embargo_salarios            – Embargo sueldos/salarios
    8.  embargo_inmuebles           – Embargo bienes inmuebles
    9.  regularizacion_reta         – Regularización RETA
    10. liquidacion_ibi             – Liquidación IBI
    11. liquidacion_ivtm            – Liquidación IVTM (vehículos)
    12. liquidacion_iae             – Liquidación IAE
    13. liquidacion_plusvalia        – Liquidación plusvalía (IIVTNU)
    14. liquidacion_icio             – Liquidación ICIO
    15. liquidacion_tasas            – Tasas municipales (basura, agua, etc.)
    16. recibo_ibi                   – Recibo IBI
    17. recibo_ivtm                  – Recibo IVTM
    18. recibo_iae                   – Recibo IAE
    19. recibo_tasas                 – Recibo tasas/precios públicos
    20. sancion_trafico              – Multa de tráfico
    21. sancion_urbanistica          – Sanción urbanística
    22. sancion_tributaria           – Sanción tributaria
    23. requerimiento_pago           – Requerimiento de pago
    24. requerimiento_informacion    – Requerimiento de información
    25. notificacion_dehu            – Notificación DEHú/DEH
    26. acta_inspeccion              – Acta de inspección
    27. carta_pago                   – Carta de pago / autoliquidación
    28. certificado_corriente        – Certificado estar al corriente
    29. certificado_deudas           – Certificado de deudas
    30. certificado_empadronamiento  – Certificado de empadronamiento
    31. resolucion_recurso           – Resolución recurso reposición
    32. aplazamiento_fraccionamiento – Aplazamiento/fraccionamiento
    33. notificacion_catastro        – Notificación catastral
    34. alta_padron                  – Alta/modificación padrón fiscal
    35. compensacion_deudas          – Compensación de deudas
    36. declaracion_responsable      – Declaración de responsabilidad
    37. _generico                    – Fallback genérico
═══════════════════════════════════════════════════════════════════════════════
"""

ETIQUETAS_POR_TIPO = {

    # ═══════════════════════════════════════════════════════════════════════
    # 1. PROVISIÓ DE CONSTRENYIMENT (Ajuntament BCN / ORGT / Diputació)
    # ═══════════════════════════════════════════════════════════════════════
    "provisio_constrenyiment": {
        "nif":            ["NIF", "CIF", "NIF/CIF", "DNI/NIF"],
        "referencia":     ["Referència", "Referencia", "Ref.", "Ref",
                           "Núm. de provisió", "Num. provisió", "Número de provisió",
                           "Núm provisió", "Núm. de rebut", "Número de rebut", "Num rebut",
                           "Clau de liquidació", "Núm. expedient"],
        "fecha":          ["Data d’emissió", "Data emissió", "Data de la provisió",
                           "Data provisió", "Data de provisió", "Fecha emisión"],
        "sujeto":         ["Càrrec", "Cargo", "Referencia càrrec", "Identificació"],
        "referencia_cat": ["Referència", "Referencia", "Ref.", "Ref", "Identificació"],
        "fecha_emissio":  ["Data d'emissió", "Data emissió", "Fecha emisión"],
        "concepte":       ["Concepte", "Concepto", "Concepte tributari"],
        "objecte":        ["Objecte", "Objeto", "Objecte tributari",
                           "Matrícula", "Ref. cadastral", "Referència cadastral"],
        "adreca":         ["Adreça tributària", "Adreça", "Dirección fiscal",
                           "Domicili fiscal", "Domicili"],
        "nom":            ["Nom i cognoms o raó social", "Nom", "Nom i cognoms", "Cognoms i nom",
                           "Raó social", "Contribuent", "Obligat tributari",
                           "Subjecte passiu", "Deutor"],
        "carrega":        ["Càrrec", "Càrrega", "Cargo", "Referencia càrrec"],
        "periode":        ["Període", "Periodo", "Período", "Exercici"],
        "importe":        ["Import", "Importe", "Import total",
                           "Import del deute", "Import principal"],
        "recarrec":       ["Recàrrec", "Recargo", "Recàrrec de constrenyiment",
                           "Recàrrec executiu"],
        "interessos":     ["Interessos", "Intereses", "Interessos de demora",
                           "Int. demora"],
        "costes":         ["Costes", "Costas", "Costes del procediment"],
        "total":          ["Total del deute", "Total a ingressar", "Total a pagar", "Import total",
                           "Total deute", "Total"],
        "lot":            ["Núm. de lot", "Número de lot", "Lot"],
        "csv":            ["CSV", "Codi segur", "Codi de verificació",
                           "Codi Segur de Verificació"],
        "boundary_tags":  ["Identificació", "Dades per fer", "Codi de pagament",
                           "Codi Procediment Recaptació", "L’obtenció de còpies",
                           "Puc reclamar?", "Persona que", "Persona que està obligada a pagar",
                           "Detall del deute", "Total del deute"],
        "organisme":      ["Organisme", "Organismo", "Ajuntament",
                           "Diputació", "ORGT", "Òrgan emissor"],
        "compte":         ["Compte d'ingrés", "Compte bancari", "IBAN",
                           "Entitat financera"],
        "termini":        ["Termini d'ingrés", "Termini", "Data límit",
                           "Termini voluntari"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 2. PROVIDENCIA DE APREMIO (AEAT – estatal)
    # ═══════════════════════════════════════════════════════════════════════
    "providencia_apremio": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "N.I.F", "N.I.F."],
        "nombre":           ["Nombre o razón social", "Denominación", "Razón social",
                             "Nombre", "Apellidos y nombre", "Contribuyente",
                             "Obligado tributario", "Deudor"],
        "domicilio":        ["Domicilio fiscal", "Dirección fiscal", "Domicilio",
                             "Dirección"],
        "referencia":       ["Clave de liquidación", "Referencia", "Ref.",
                             "Nº liquidación", "Número de liquidación",
                             "Núm. expediente", "Expediente", "Nº expediente"],
        "importe":          ["Principal pendiente", "Importe principal", "Deuda",
                             "Importe de la deuda", "Importe total", "Importe"],
        "importe_recargo":  ["Recargo de apremio ordinario (20%)", "Recargo ordinario",
                             "Recargo de apremio reducido (10%)", "Recargo reducido",
                             "Recargo ejecutivo", "Importe recargo", "Recargo"],
        "intereses":        ["Intereses de demora", "Int. demora", "Intereses"],
        "costas":           ["Costas del procedimiento", "Costas"],
        "total":            ["Importe Total", "Importe total a ingresar", "Total a ingresar",
                             "Total deuda", "Total a pagar", "Total"],
        "fecha":            ["Fecha de emisión", "Fecha emisión", "Fecha de la providencia",
                             "Fecha"],
        "periodo":          ["Ejercicio/Período", "Período", "Periodo", "Ejercicio"],
        "concepto":         ["Concepto tributario", "Concepto", "Tributo",
                             "Tipo de tributo", "Descripción"],
        "objeto":           ["Objeto tributario", "Objeto", "Matrícula",
                             "Ref. catastral", "Referencia catastral"],
        "providencia_num":  ["Providencia de apremio", "Núm. providencia",
                             "Providencia", "Nº providencia", "Núm."],
        "csv":              ["Código seguro de verificación", "Código seguro",
                             "Código de verificación", "CSV", "C.S.V."],
        "organismo":        ["U.REC. DE LETAMENDI", "Agencia Tributaria", "AEAT",
                             "Delegación", "Administración de Hacienda"],
        "cuenta":           ["Cuenta de ingreso", "IBAN", "Entidad financiera",
                             "Código cuenta"],
        "plazo":            ["Plazo de ingreso", "Plazo", "Fecha límite",
                             "Fecha fin voluntaria"],
        "boundary_tags":    ["INTERESES Y COSTAS", "PLAZOS DE PAGO", "LUGAR Y FORMAS DE PAGO",
                             "CONSECUENCIAS DE LA FALTA DE PAGO", "SOLICITUD DE APLAZAMIENTO",
                             "RECURSOS Y RECLAMACIONES", "NORMAS APLICABLES",
                             "IDENTIFICACIÓN DEL OBLIGADO", "ACUERDO", "IMPORTE DE LA DEUDA"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 3. PROVIDENCIA DE APREMIO (Ayuntamientos / Diputaciones – local)
    #    Incluye variantes CA, VA, EU, GL
    # ═══════════════════════════════════════════════════════════════════════
    "providencia_apremio_local": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "N.I.F", "DNI/NIF",
                             # EU
                             "IFZ", "IFK", "NAN/IFZ"],
        "nombre":           ["Nombre", "Razón social", "Contribuyente",
                             "Obligado tributario", "Sujeto pasivo", "Deudor",
                             # CA/VA
                             "Nom", "Nom i cognoms", "Raó social",
                             "Contribuent", "Obligat tributari", "Deutor",
                             # EU
                             "Izena", "Izen-abizenak", "Sozietatearen izena",
                             "Zergaduna", "Zerga-obligatua", "Zorduna",
                             # GL
                             "Nome", "Nome e apelidos", "Contribuínte",
                             "Obrigado tributario", "Debedor"],
        "domicilio":        ["Domicilio", "Domicilio fiscal", "Dirección",
                             # CA/VA
                             "Domicili", "Domicili fiscal", "Adreça",
                             "Adreça tributària",
                             # EU
                             "Helbidea", "Zerga-helbidea",
                             # GL
                             "Enderezo", "Enderezo fiscal"],
        "referencia":       ["Referencia", "Ref.", "Nº expediente", "Expediente",
                             "Clave de liquidación", "Nº liquidación",
                             "Nº providencia", "Providencia",
                             # CA/VA
                             "Referència", "Núm. expedient", "Expedient",
                             "Clau de liquidació", "Núm. provisió",
                             "Núm. de rebut",
                             # EU
                             "Erreferentzia", "Erref.", "Espediente zk.",
                             "Espedientea", "Likidazio-gakoa",
                             "Probidentzia zk.",
                             # GL
                             "Núm. expediente", "Núm. providencia"],
        "importe":          ["Importe", "Importe total", "Importe de la deuda",
                             "Principal", "Deuda",
                             # CA/VA
                             "Import", "Import total", "Import del deute",
                             # EU
                             "Zenbatekoa", "Guztizko zenbatekoa",
                             "Zor-zenbatekoa", "Printzipal",
                             # GL
                             "Importe da débeda", "Débeda"],
        "recargo":          ["Recargo", "Recargo de apremio", "Recargo ejecutivo",
                             # CA/VA
                             "Recàrrec", "Recàrrec de constrenyiment",
                             "Recàrrec executiu",
                             # EU
                             "Errekargua", "Premiamendu-errekargua",
                             # GL
                             "Recarga", "Recarga de constrinximento",
                             "Recarga executiva"],
        "intereses":        ["Intereses", "Intereses de demora",
                             # CA/VA
                             "Interessos", "Interessos de demora",
                             # EU
                             "Berandutza-interesak", "Interesak",
                             # GL
                             "Xuros", "Xuros de demora"],
        "costas":           ["Costas", "Costas del procedimiento",
                             # CA/VA
                             "Costes", "Costes del procediment",
                             # EU
                             "Kostuak", "Prozeduraren kostuak",
                             # GL
                             "Custas", "Custas do procedemento"],
        "total":            ["Total a ingresar", "Total a pagar",
                             "Importe total a ingresar", "Total deuda", "Total",
                             # CA/VA
                             "Total a ingressar", "Import total", "Total deute",
                             # EU
                             "Guztira ordaindu beharrekoa", "Guztira",
                             "Guztizko zorra",
                             # GL
                             "Total débeda"],
        "fecha":            ["Fecha", "Fecha de la providencia", "Fecha emisión",
                             # CA/VA
                             "Data", "Data de la provisió", "Data d'emissió",
                             "Data emissió",
                             # EU
                             "Data", "Probidentziaren data", "Jaulkipen-data",
                             # GL
                             "Data da providencia", "Data de emisión"],
        "periodo":          ["Período", "Periodo", "Ejercicio",
                             # CA/VA
                             "Període", "Exercici",
                             # EU
                             "Aldia", "Ekitaldia",
                             # GL
                             "Exercicio"],
        "concepto":         ["Concepto", "Tributo", "Concepto tributario",
                             # CA/VA
                             "Concepte", "Tribut", "Concepte tributari",
                             # EU
                             "Kontzeptua", "Zerga", "Zerga-kontzeptua",
                             # GL
                             "Concepto tributario"],
        "objeto":           ["Objeto tributario", "Matrícula", "Ref. catastral",
                             "Referencia catastral",
                             # CA/VA
                             "Objecte", "Objecte tributari",
                             "Ref. cadastral", "Referència cadastral",
                             # EU
                             "Objektua", "Zerga-objektua", "Matrikula",
                             "Katastroko erreferentzia",
                             # GL
                             "Obxecto", "Obxecto tributario"],
        "csv":              ["CSV", "Código seguro de verificación", "C.S.V.",
                             # CA/VA
                             "Codi segur de verificació",
                             # EU
                             "Egiaztapen-kode segurua"],
        "organismo":        ["Ayuntamiento", "Diputación", "Organismo",
                             "Órgano de recaudación", "Tesorería",
                             # CA/VA
                             "Ajuntament", "Diputació", "Organisme",
                             "ORGT", "SUMA", "XALOC", "BASE",
                             # EU
                             "Udala", "Foru Aldundia", "Erakundea",
                             "Bilketa-erakundea",
                             # GL
                             "Concello", "Deputación", "Organismo"],
        "cuenta":           ["Cuenta de ingreso", "IBAN", "Entidad financiera",
                             # CA/VA
                             "Compte d'ingrés", "Compte bancari",
                             # EU
                             "Sarrera-kontua", "IBAN", "Banku-kontua",
                             # GL
                             "Conta de ingreso", "Conta bancaria"],
        "plazo":            ["Plazo de ingreso", "Fecha límite",
                             # CA/VA
                             "Termini d'ingrés", "Data límit",
                             # EU
                             "Sarrera-epea", "Muga-data",
                             # GL
                             "Prazo de ingreso", "Data límite"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 4. EMBARGO DE VEHÍCULOS (TGSS)
    # ═══════════════════════════════════════════════════════════════════════
    "embargo_vehiculos": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Apellidos y nombre"],
        "expediente":       ["Expediente", "Núm. expediente", "N.º expediente",
                             "Nº expediente"],
        "importe_total":    ["Importe total", "Total", "Deuda total",
                             "Total a embargar"],
        "importe_principal":["Principal", "Importe principal"],
        "importe_recargo":  ["Recargo", "Importe recargo", "Recargo de apremio"],
        "vehiculos":        ["Matrícula", "Vehículo", "Vehículos",
                             "Marca", "Modelo", "Marca y modelo",
                             "Nº bastidor", "Bastidor"],
        "fecha":            ["Fecha", "Fecha de la diligencia",
                             "Fecha del embargo"],
        "csv":              ["CSV", "Código seguro", "Código de verificación"],
        "organismo":        ["Tesorería General de la Seguridad Social",
                             "TGSS", "Dirección Provincial"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 5. EMBARGO DE CUENTAS (TGSS)
    # ═══════════════════════════════════════════════════════════════════════
    "embargo_cuentas": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Apellidos y nombre"],
        "expediente":       ["Expediente", "Núm. expediente", "N.º expediente"],
        "importe_embargado":["Importe a embargar", "Embargado",
                             "Importe embargado", "Cantidad embargada"],
        "entidad":          ["Entidad financiera", "Banco", "Entidad",
                             "Caja", "Entidad de crédito", "Sucursal"],
        "cuenta":           ["Cuenta", "Nº cuenta", "IBAN", "Cuenta bancaria"],
        "fecha":            ["Fecha", "Fecha de la diligencia",
                             "Fecha del embargo"],
        "csv":              ["CSV", "Código seguro"],
        "organismo":        ["TGSS", "Tesorería General de la Seguridad Social"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 6. EMBARGO DE CUENTAS (AEAT / Ayuntamientos)
    # ═══════════════════════════════════════════════════════════════════════
    "embargo_cuentas_aeat": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "N.I.F"],
        "nombre":           ["Nombre", "Razón social", "Obligado tributario",
                             "Contribuyente", "Deudor"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "expediente":       ["Expediente", "Nº expediente", "Nº diligencia",
                             "Núm. diligencia", "Referencia"],
        "importe_embargado":["Importe a embargar", "Importe embargado",
                             "Cantidad embargada", "Importe total",
                             "Deuda pendiente"],
        "entidad":          ["Entidad financiera", "Banco", "Entidad",
                             "Caja", "Entidad de crédito"],
        "cuenta":           ["Cuenta", "Nº cuenta", "IBAN", "Cuenta bancaria"],
        "deuda_origen":     ["Deuda origen", "Concepto", "Tributo",
                             "Descripción"],
        "fecha":            ["Fecha", "Fecha de la diligencia",
                             "Fecha del embargo", "Fecha emisión"],
        "periodo":          ["Período", "Periodo", "Ejercicio"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Agencia Tributaria", "Ayuntamiento",
                             "Diputación", "Órgano de recaudación",
                             "Tesorería"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 7. EMBARGO DE SALARIOS / SUELDOS
    # ═══════════════════════════════════════════════════════════════════════
    "embargo_salarios": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre_deudor":    ["Nombre del deudor", "Deudor", "Obligado al pago",
                             "Embargado"],
        "nombre_pagador":   ["Pagador", "Empresa", "Empleador",
                             "Nombre del pagador", "Razón social pagador"],
        "expediente":       ["Expediente", "Nº expediente", "Referencia"],
        "importe_deuda":    ["Importe de la deuda", "Deuda total",
                             "Importe total pendiente"],
        "retencion":        ["Retención", "Cantidad a retener",
                             "Importe a retener mensualmente",
                             "Retención mensual"],
        "smi":              ["SMI", "Salario Mínimo Interprofesional",
                             "Mínimo inembargable"],
        "escala":           ["Escala", "Porcentaje de retención",
                             "Tramo", "Porcentaje"],
        "fecha":            ["Fecha", "Fecha de la diligencia"],
        "csv":              ["CSV", "Código seguro"],
        "organismo":        ["AEAT", "TGSS", "Ayuntamiento", "Juzgado",
                             "Agencia Tributaria", "Órgano de recaudación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 8. EMBARGO DE BIENES INMUEBLES
    # ═══════════════════════════════════════════════════════════════════════
    "embargo_inmuebles": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Deudor",
                             "Obligado tributario"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "expediente":       ["Expediente", "Nº expediente", "Referencia"],
        "finca":            ["Finca", "Nº finca", "Finca registral",
                             "Número de finca"],
        "registro":         ["Registro de la Propiedad", "Registro",
                             "Nº registro", "Tomo", "Libro", "Folio"],
        "ref_catastral":    ["Referencia catastral", "Ref. catastral",
                             "Ref. Catastral"],
        "situacion":        ["Situación", "Dirección del inmueble",
                             "Ubicación", "Situación del bien"],
        "descripcion":      ["Descripción", "Descripción del bien",
                             "Naturaleza", "Tipo de inmueble",
                             "Urbana", "Rústica"],
        "importe_deuda":    ["Deuda", "Importe de la deuda", "Total adeudado",
                             "Importe total"],
        "anotacion":        ["Anotación preventiva", "Mandamiento",
                             "Anotación de embargo"],
        "fecha":            ["Fecha", "Fecha de la diligencia",
                             "Fecha del embargo"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Ayuntamiento", "TGSS",
                             "Agencia Tributaria"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 9. REGULARIZACIÓN RETA
    # ═══════════════════════════════════════════════════════════════════════
    "regularizacion_reta": {
        "nif":     ["NIF", "NIF/CIF", "CIF"],
        "nombre":  ["Nombre", "Razón social", "Apellidos", "Apellidos y nombre"],
        "naf":     ["NAF", "Núm. afiliación", "N.º afiliación",
                    "Número de afiliación"],
        "importe": ["Importe", "Cuota", "Importe a ingresar",
                    "Importe devolución", "Resultado regularización",
                    "Diferencia de cuotas"],
        "iban":    ["IBAN", "Cuenta bancaria", "Cuenta de ingreso",
                    "Cuenta de devolución"],
        "regimen": ["Régimen", "Régimen especial", "RETA",
                    "Régimen Especial de Trabajadores Autónomos"],
        "base":    ["Base de cotización", "Base reguladora",
                    "Base de cotización definitiva",
                    "Base de cotización provisional"],
        "periodo": ["Período", "Periodo", "Ejercicio", "Año"],
        "fecha":   ["Fecha", "Fecha de la resolución", "Fecha emisión"],
        "csv":     ["CSV", "Código seguro"],
        "organismo": ["TGSS", "Tesorería General de la Seguridad Social",
                      "Seguridad Social"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 10. LIQUIDACIÓN IBI (todos los idiomas)
    # ═══════════════════════════════════════════════════════════════════════
    "liquidacion_ibi": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "DNI",
                             "IFZ", "IFK"],
        "nombre":           ["Nombre", "Contribuyente", "Sujeto pasivo",
                             "Obligado tributario", "Titular",
                             # CA/VA
                             "Nom", "Contribuent", "Subjecte passiu",
                             "Obligat tributari", "Titular",
                             # EU
                             "Izena", "Zergaduna", "Subjektu pasiboa",
                             # GL
                             "Nome", "Contribuínte", "Suxeito pasivo"],
        "domicilio":        ["Domicilio", "Domicilio fiscal",
                             "Domicili", "Domicili fiscal", "Adreça",
                             "Helbidea", "Zerga-helbidea",
                             "Enderezo", "Enderezo fiscal"],
        "ref_catastral":    ["Referencia catastral", "Ref. catastral",
                             "Ref. Catastral",
                             "Referència cadastral", "Ref. cadastral",
                             "Katastro-erreferentzia",
                             "Referencia catastral"],
        "situacion":        ["Situación del inmueble", "Dirección del inmueble",
                             "Situación", "Ubicación",
                             "Situació de l'immoble", "Adreça de l'immoble",
                             "Higiezinaren kokalekua", "Higiezinaren helbidea",
                             "Situación do inmoble"],
        "uso":              ["Uso", "Clase", "Naturaleza",
                             "Urbana", "Rústica", "BICE",
                             "Ús", "Classe",
                             "Erabilera", "Mota"],
        "valor_catastral":  ["Valor catastral", "V. catastral",
                             "Valor del suelo", "Valor de construcción",
                             "Valor cadastral", "V. cadastral",
                             "Valor del sòl", "Valor de construcció",
                             "Katastro-balioa", "Lurzoru-balioa",
                             "Eraikuntza-balioa"],
        "base_imponible":   ["Base imponible", "Base liquidable", "B.I.",
                             "Base imposable", "Base liquidable",
                             "Zerga-oinarria", "Oinarri likidagarria",
                             "Base impoñible"],
        "tipo_gravamen":    ["Tipo de gravamen", "Tipo impositivo", "Tipo",
                             "Tipus de gravamen", "Tipus impositiu",
                             "Karga-tasa", "Zerga-tasa",
                             "Tipo de gravame"],
        "cuota":            ["Cuota", "Cuota íntegra", "Cuota líquida",
                             "Cuota tributaria",
                             "Quota", "Quota íntegra", "Quota líquida",
                             "Kuota", "Kuota osoa", "Kuota likidoa",
                             "Cota", "Cota íntegra"],
        "bonificacion":     ["Bonificación", "Exención", "Reducción",
                             "Deducción",
                             "Bonificació", "Exempció", "Reducció",
                             "Hobaria", "Salbuespena", "Murrizketa",
                             "Bonificación", "Exención", "Redución"],
        "recargo":          ["Recargo", "Recàrrec", "Errekargua", "Recarga"],
        "total":            ["Total", "Total a ingresar", "Deuda tributaria",
                             "Importe total", "A ingresar",
                             "Total a ingressar", "Deute tributari",
                             "Guztira", "Guztira sartu beharrekoa",
                             "Zerga-zorra",
                             "Total a ingresar", "Débeda tributaria"],
        "periodo":          ["Período", "Ejercicio", "Devengo", "Año",
                             "Període", "Exercici", "Meritació",
                             "Aldia", "Ekitaldia", "Sortzapena",
                             "Exercicio"],
        "fecha":            ["Fecha", "Fecha emisión", "Fecha de la liquidación",
                             "Data", "Data emissió", "Data de la liquidació",
                             "Jaulkipen-data", "Likidazioaren data",
                             "Data emisión"],
        "concepto":         ["IBI", "Impuesto sobre Bienes Inmuebles",
                             "Impost sobre Béns Immobles",
                             "Ondasun Higiezinen gaineko Zerga", "OHZ",
                             "Imposto sobre Bens Inmobles"],
        "csv":              ["CSV", "Código seguro de verificación",
                             "Codi segur de verificació",
                             "Egiaztapen-kode segurua"],
        "organismo":        ["Ayuntamiento", "Diputación",
                             "Ajuntament", "Diputació", "ORGT", "SUMA",
                             "Udala", "Foru Aldundia",
                             "Concello", "Deputación"],
        "plazo":            ["Plazo de ingreso", "Plazo voluntario",
                             "Fecha fin voluntaria",
                             "Termini d'ingrés", "Termini voluntari",
                             "Sarrera-epea", "Borondatezko epea",
                             "Prazo de ingreso", "Prazo voluntario"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 11. LIQUIDACIÓN IVTM (Impuesto Vehículos Tracción Mecánica)
    # ═══════════════════════════════════════════════════════════════════════
    "liquidacion_ivtm": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "IFZ"],
        "nombre":           ["Nombre", "Contribuyente", "Titular",
                             "Nom", "Contribuent", "Titular",
                             "Izena", "Zergaduna", "Titularra",
                             "Nome", "Contribuínte"],
        "domicilio":        ["Domicilio", "Domicilio fiscal",
                             "Domicili", "Adreça",
                             "Helbidea",
                             "Enderezo"],
        "matricula":        ["Matrícula", "Vehículo", "Marca y modelo",
                             "Marca", "Modelo", "Tipo de vehículo",
                             "Nº bastidor", "Cilindrada", "CVF",
                             "Caballos fiscales", "Potencia fiscal",
                             "Matrícula", "Vehicle", "Marca i model",
                             "Matrikula", "Ibilgailua",
                             "Vehículo", "Marca e modelo"],
        "clase_vehiculo":   ["Clase", "Tipo", "Turismo", "Motocicleta",
                             "Camión", "Autobús", "Ciclomotor", "Remolque",
                             "Classe", "Tipus",
                             "Mota"],
        "cuota":            ["Cuota", "Cuota tributaria", "Cuota íntegra",
                             "Quota", "Kuota", "Cota"],
        "bonificacion":     ["Bonificación", "Exención",
                             "Vehículo histórico", "Eléctrico",
                             "Bonificació", "Hobaria"],
        "total":            ["Total", "Total a ingresar", "Importe",
                             "Total a ingressar", "Import",
                             "Guztira", "Total a ingresar"],
        "periodo":          ["Período", "Ejercicio", "Año",
                             "Període", "Exercici",
                             "Aldia", "Ekitaldia",
                             "Exercicio"],
        "fecha":            ["Fecha", "Fecha emisión",
                             "Data", "Data emissió",
                             "Data", "Jaulkipen-data"],
        "concepto":         ["IVTM", "Impuesto sobre Vehículos",
                             "Impuesto sobre Vehículos de Tracción Mecánica",
                             "Impost sobre Vehicles de Tracció Mecànica",
                             "Ibilgailu Mekanikoen gaineko Zerga", "IOMZ",
                             "Imposto sobre Vehículos de Tracción Mecánica"],
        "csv":              ["CSV", "Código seguro de verificación",
                             "Codi segur de verificació",
                             "Egiaztapen-kode segurua"],
        "organismo":        ["Ayuntamiento", "Ajuntament", "Udala",
                             "Concello", "ORGT", "SUMA", "Diputación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 12. LIQUIDACIÓN IAE (Impuesto Actividades Económicas)
    # ═══════════════════════════════════════════════════════════════════════
    "liquidacion_iae": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Denominación",
                             "Contribuyente", "Sujeto pasivo"],
        "domicilio":        ["Domicilio", "Domicilio fiscal",
                             "Domicilio de la actividad"],
        "epigrafe":         ["Epígrafe", "Nº epígrafe", "Código IAE",
                             "Actividad", "Actividad económica",
                             "Sección", "División", "Grupo"],
        "cuota_municipal":  ["Cuota municipal", "Cuota mínima municipal"],
        "cuota_provincial": ["Cuota provincial"],
        "cuota_nacional":   ["Cuota nacional"],
        "coeficiente":      ["Coeficiente de ponderación",
                             "Coeficiente de situación",
                             "Coeficiente", "Índice"],
        "superficie":       ["Superficie", "M²", "Metros cuadrados",
                             "Superficie del local"],
        "cuota":            ["Cuota", "Cuota tributaria"],
        "bonificacion":     ["Bonificación", "Exención"],
        "total":            ["Total", "Total a ingresar", "Importe"],
        "periodo":          ["Período", "Ejercicio", "Año"],
        "fecha":            ["Fecha", "Fecha emisión"],
        "concepto":         ["IAE", "Impuesto sobre Actividades Económicas",
                             "Impost sobre Activitats Econòmiques",
                             "Jarduera Ekonomikoen gaineko Zerga", "JEZ",
                             "Imposto sobre Actividades Económicas"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "AEAT", "Diputación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 13. LIQUIDACIÓN PLUSVALÍA (IIVTNU)
    # ═══════════════════════════════════════════════════════════════════════
    "liquidacion_plusvalia": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Sujeto pasivo", "Transmitente",
                             "Adquirente", "Contribuyente"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "ref_catastral":    ["Referencia catastral", "Ref. catastral"],
        "situacion":        ["Situación del inmueble", "Dirección del terreno",
                             "Ubicación"],
        "fecha_transmision":["Fecha de transmisión", "Fecha transmisión",
                             "Fecha de la operación", "Fecha del hecho imponible"],
        "tipo_transmision": ["Tipo de transmisión", "Causa",
                             "Compraventa", "Herencia", "Donación",
                             "Inter vivos", "Mortis causa"],
        "valor_suelo":      ["Valor del suelo", "Valor catastral del suelo",
                             "Valor del terreno"],
        "porcentaje_transmision": ["Porcentaje de transmisión", "% transmitido",
                                    "Cuota de participación"],
        "periodo_generacion":["Período de generación", "Años de tenencia",
                              "Período de titularidad", "Nº años"],
        "base_imponible":   ["Base imponible", "Base liquidable",
                             "Incremento de valor"],
        "tipo_gravamen":    ["Tipo de gravamen", "Tipo impositivo"],
        "cuota":            ["Cuota", "Cuota íntegra", "Cuota tributaria"],
        "bonificacion":     ["Bonificación", "Exención", "Reducción"],
        "total":            ["Total", "Total a ingresar", "Deuda tributaria"],
        "plazo":            ["Plazo", "Plazo de ingreso", "Plazo de presentación"],
        "fecha":            ["Fecha", "Fecha emisión", "Fecha de la liquidación"],
        "concepto":         ["IIVTNU", "Plusvalía",
                             "Impuesto sobre el Incremento del Valor de los Terrenos",
                             "Impuesto sobre el Incremento de Valor de los Terrenos de Naturaleza Urbana"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "Hacienda municipal"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 14. LIQUIDACIÓN ICIO
    # ═══════════════════════════════════════════════════════════════════════
    "liquidacion_icio": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Sujeto pasivo", "Titular de la licencia",
                             "Promotor"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "licencia":         ["Nº licencia", "Licencia de obras",
                             "Licencia urbanística", "Expediente de obras"],
        "ubicacion_obra":   ["Ubicación de la obra", "Dirección de la obra",
                             "Emplazamiento"],
        "coste_obra":       ["Coste real de la obra", "Presupuesto de ejecución",
                             "Coste de ejecución material",
                             "Presupuesto", "Coste real"],
        "base_imponible":   ["Base imponible", "Coste real y efectivo"],
        "tipo_gravamen":    ["Tipo de gravamen", "Tipo impositivo"],
        "cuota":            ["Cuota", "Cuota tributaria"],
        "bonificacion":     ["Bonificación", "Exención"],
        "total":            ["Total", "Total a ingresar"],
        "fecha":            ["Fecha", "Fecha emisión"],
        "concepto":         ["ICIO", "Impuesto sobre Construcciones",
                             "Impuesto sobre Construcciones, Instalaciones y Obras"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 15. LIQUIDACIÓN TASAS MUNICIPALES (basura, agua, alcantarillado…)
    # ═══════════════════════════════════════════════════════════════════════
    "liquidacion_tasas": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "IFZ"],
        "nombre":           ["Nombre", "Contribuyente", "Titular", "Abonado",
                             "Nom", "Contribuent", "Abonat",
                             "Izena", "Zergaduna",
                             "Nome", "Contribuínte"],
        "domicilio":        ["Domicilio", "Domicilio fiscal", "Dirección",
                             "Domicili", "Adreça",
                             "Helbidea",
                             "Enderezo"],
        "referencia":       ["Referencia", "Nº recibo", "Contrato",
                             "Nº contrato", "Nº suministro", "Nº abonado",
                             "Referència", "Núm. rebut",
                             "Erreferentzia"],
        "tipo_tasa":        ["Tasa", "Concepto", "Tipo de tasa",
                             "Tasa de basuras", "Tasa de residuos",
                             "Tasa de recogida de residuos",
                             "Tasa de agua", "Tasa de abastecimiento",
                             "Tasa de alcantarillado", "Tasa de depuración",
                             "Tasa de cementerio", "Tasa de vado",
                             "Tasa de terrazas", "Tasa de ocupación",
                             "Precio público",
                             # CA/VA
                             "Taxa", "Taxa d'escombraries", "Taxa de residus",
                             "Taxa de recollida de residus",
                             "Taxa d'aigua", "Taxa d'abastament",
                             "Taxa de clavegueram", "Preu públic",
                             # EU
                             "Tasa", "Zabor-tasa", "Hondakin-tasa",
                             "Ur-tasa", "Estolderia-tasa",
                             "Prezio publikoa",
                             # GL
                             "Taxa de lixo", "Taxa de auga",
                             "Taxa de sumidoiros"],
        "consumo":          ["Consumo", "M³", "Metros cúbicos", "Lectura",
                             "Lectura anterior", "Lectura actual",
                             "Consum", "Kontsumoa"],
        "cuota":            ["Cuota", "Cuota fija", "Cuota variable",
                             "Canon", "Quota", "Kuota", "Cota"],
        "total":            ["Total", "Total a pagar", "Importe",
                             "Total a ingressar", "Guztira"],
        "periodo":          ["Período", "Bimestre", "Trimestre",
                             "Semestre", "Ejercicio", "Año",
                             "Període", "Aldia", "Exercicio"],
        "fecha":            ["Fecha", "Fecha emisión",
                             "Data", "Data emissió"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "Mancomunidad", "Consorcio",
                             "Empresa municipal de aguas",
                             "Ajuntament", "Mancomunitat", "Consorci",
                             "Udala", "Mankomunitatea",
                             "Concello", "Mancomunidade"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 16–19. RECIBOS (IBI, IVTM, IAE, TASAS) – misma estructura que
    #        liquidaciones pero con campos de domiciliación / cobro
    # ═══════════════════════════════════════════════════════════════════════
    "recibo_ibi": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "IFZ"],
        "nombre":           ["Nombre", "Contribuyente", "Titular",
                             "Nom", "Izena", "Nome"],
        "ref_catastral":    ["Referencia catastral", "Ref. catastral",
                             "Referència cadastral", "Katastro-erreferentzia"],
        "situacion":        ["Situación", "Dirección del inmueble",
                             "Situació", "Adreça de l'immoble"],
        "valor_catastral":  ["Valor catastral", "V. catastral",
                             "Valor cadastral", "Katastro-balioa"],
        "base":             ["Base imponible", "Base liquidable",
                             "Base imposable", "Zerga-oinarria",
                             "Base impoñible"],
        "tipo":             ["Tipo", "Tipo de gravamen",
                             "Tipus", "Karga-tasa"],
        "cuota":            ["Cuota", "Quota", "Kuota", "Cota"],
        "bonificacion":     ["Bonificación", "Bonificació", "Hobaria"],
        "total":            ["Total", "Total a pagar", "Importe",
                             "Importe del recibo", "A ingresar",
                             "Total a ingressar", "Import del rebut",
                             "Guztira", "Ordaindu beharrekoa"],
        "periodo":          ["Período", "Ejercicio", "Año",
                             "Període", "Aldia"],
        "domiciliacion":    ["Domiciliación", "IBAN", "Cuenta de cargo",
                             "Entidad bancaria", "Fecha de cargo",
                             "Domiciliació", "Compte de càrrec",
                             "Helbideratzea", "Kargua-kontua"],
        "voluntaria":       ["Periodo voluntario", "Plazo voluntario",
                             "Desde", "Hasta", "Inicio cobro", "Fin cobro",
                             "Període voluntari", "Des de", "Fins a",
                             "Borondatezko aldia"],
        "concepto":         ["IBI", "Impuesto sobre Bienes Inmuebles",
                             "Impost sobre Béns Immobles", "OHZ"],
        "organismo":        ["Ayuntamiento", "Diputación",
                             "Ajuntament", "ORGT", "SUMA",
                             "Udala", "Foru Aldundia",
                             "Concello", "Deputación"],
    },

    "recibo_ivtm": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Titular", "Contribuyente",
                             "Nom", "Izena", "Nome"],
        "matricula":        ["Matrícula", "Vehículo", "Marca y modelo",
                             "Cilindrada", "CVF", "Caballos fiscales",
                             "Matrikula", "Ibilgailua"],
        "cuota":            ["Cuota", "Quota", "Kuota", "Cota"],
        "bonificacion":     ["Bonificación", "Exención",
                             "Bonificació", "Hobaria"],
        "total":            ["Total", "Total a pagar", "Importe",
                             "Total a ingressar", "Guztira"],
        "periodo":          ["Período", "Ejercicio", "Año",
                             "Període", "Aldia"],
        "domiciliacion":    ["Domiciliación", "IBAN", "Cuenta de cargo",
                             "Domiciliació", "Helbideratzea"],
        "voluntaria":       ["Periodo voluntario", "Desde", "Hasta",
                             "Període voluntari", "Borondatezko aldia"],
        "concepto":         ["IVTM", "Impuesto sobre Vehículos",
                             "Impost sobre Vehicles", "IOMZ"],
        "organismo":        ["Ayuntamiento", "Ajuntament", "Udala",
                             "Concello", "ORGT", "SUMA"],
    },

    "recibo_iae": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Contribuyente"],
        "epigrafe":         ["Epígrafe", "Actividad", "Código IAE"],
        "cuota":            ["Cuota", "Cuota municipal"],
        "coeficiente":      ["Coeficiente de ponderación",
                             "Coeficiente de situación"],
        "total":            ["Total", "Total a pagar", "Importe"],
        "periodo":          ["Período", "Ejercicio"],
        "domiciliacion":    ["Domiciliación", "IBAN", "Cuenta de cargo"],
        "voluntaria":       ["Periodo voluntario", "Desde", "Hasta"],
        "concepto":         ["IAE", "Impuesto sobre Actividades Económicas",
                             "Impost sobre Activitats Econòmiques", "JEZ"],
        "organismo":        ["Ayuntamiento", "AEAT", "Diputación"],
    },

    "recibo_tasas": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Contribuyente", "Titular", "Abonado",
                             "Nom", "Izena", "Nome"],
        "referencia":       ["Referencia", "Nº recibo", "Contrato",
                             "Referència", "Erreferentzia"],
        "tipo_tasa":        ["Tasa", "Concepto",
                             "Basuras", "Residuos", "Agua", "Alcantarillado",
                             "Cementerio", "Vado",
                             "Taxa", "Escombraries", "Aigua",
                             "Zabor-tasa", "Ur-tasa",
                             "Lixo", "Auga"],
        "consumo":          ["Consumo", "M³", "Lectura",
                             "Consum", "Kontsumoa"],
        "total":            ["Total", "Total a pagar", "Importe",
                             "Total a ingressar", "Guztira"],
        "periodo":          ["Período", "Bimestre", "Trimestre",
                             "Període", "Aldia"],
        "domiciliacion":    ["Domiciliación", "IBAN",
                             "Domiciliació", "Helbideratzea"],
        "voluntaria":       ["Periodo voluntario", "Desde", "Hasta",
                             "Període voluntari", "Borondatezko aldia"],
        "organismo":        ["Ayuntamiento", "Mancomunidad",
                             "Ajuntament", "Udala", "Concello"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 20. SANCIÓN / MULTA DE TRÁFICO
    # ═══════════════════════════════════════════════════════════════════════
    "sancion_trafico": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "DNI",
                             "IFZ", "NAN"],
        "nombre":           ["Nombre", "Denunciado", "Infractor",
                             "Titular del vehículo", "Conductor", "Interesado",
                             # CA/VA
                             "Nom", "Denunciat", "Infractor",
                             "Titular del vehicle", "Conductor",
                             # EU
                             "Izena", "Salatua", "Arau-hauslua",
                             "Ibilgailuaren titularra", "Gidaria",
                             # GL
                             "Nome", "Denunciado", "Condutor"],
        "domicilio":        ["Domicilio", "Dirección",
                             "Domicili", "Adreça",
                             "Helbidea",
                             "Enderezo"],
        "expediente":       ["Nº expediente", "Expediente sancionador",
                             "Nº denuncia", "Boletín", "Nº boletín",
                             "Referencia",
                             "Núm. expedient", "Expedient sancionador",
                             "Núm. denúncia", "Butlletí",
                             "Espediente zk.", "Zehapen-espedientea",
                             "Salaketa zk.", "Buletina"],
        "matricula":        ["Matrícula", "Vehículo", "Marca y modelo",
                             "Vehicle", "Marca i model",
                             "Matrikula", "Ibilgailua"],
        "infraccion":       ["Infracción", "Tipo de infracción",
                             "Hecho denunciado", "Precepto infringido",
                             "Artículo", "Art.", "Norma infringida",
                             "Descripción de los hechos",
                             "Infracció", "Fet denunciat",
                             "Precepte infringit", "Article",
                             "Arau-haustea", "Salatutako egitatea",
                             "Hautsitako araua", "Artikulua",
                             "Feito denunciado", "Precepto infrinxido"],
        "lugar":            ["Lugar", "Lugar de la infracción", "Calle",
                             "Dirección de la infracción", "Vía", "PK",
                             "Lloc", "Lloc de la infracció", "Carrer",
                             "Lekua", "Arau-haustearen lekua", "Kalea",
                             "Rúa"],
        "fecha_infraccion": ["Fecha de la infracción", "Fecha y hora",
                             "Fecha denuncia", "Fecha de los hechos", "Hora",
                             "Data de la infracció", "Data i hora",
                             "Data denúncia",
                             "Arau-haustearen data", "Data eta ordua",
                             "Data da infracción"],
        "gravedad":         ["Gravedad", "Calificación",
                             "Leve", "Grave", "Muy grave",
                             "Gravetat", "Lleu", "Greu", "Molt greu",
                             "Larritasuna", "Arina", "Larria", "Oso larria",
                             "Gravidade", "Moi grave"],
        "puntos":           ["Puntos", "Pérdida de puntos",
                             "Detracción de puntos",
                             "Punts", "Pèrdua de punts",
                             "Puntuak", "Puntu-galera"],
        "importe":          ["Importe", "Sanción", "Multa",
                             "Cuantía de la sanción", "Importe de la multa",
                             "Import", "Sanció", "Multa",
                             "Zenbatekoa", "Zehapena", "Isuna",
                             "Contía da sanción"],
        "reduccion":        ["Reducción", "Reducción por pronto pago",
                             "Descuento", "Importe reducido",
                             "Pago con reducción", "50%",
                             "Reducció", "Pagament amb reducció",
                             "Murrizketa", "Ordainketa azkarreko murrizketa",
                             "Redución", "Pagamento con redución"],
        "plazo":            ["Plazo", "Plazo de alegaciones", "Plazo de pago",
                             "Plazo para recurrir",
                             "Termini", "Termini d'al·legacions",
                             "Epea", "Alegazioen epea", "Ordainketa-epea",
                             "Prazo", "Prazo de alegacións"],
        "fecha_notificacion":["Fecha de notificación", "Fecha notificación",
                              "Fecha de la resolución",
                              "Data de notificació", "Data resolució",
                              "Jakinarazpen-data", "Ebazpen-data",
                              "Data de notificación"],
        "cuenta":           ["Cuenta de ingreso", "IBAN", "Forma de pago",
                             "Compte d'ingrés", "Forma de pagament",
                             "Sarrera-kontua", "Ordainketa-modua",
                             "Conta de ingreso"],
        "csv":              ["CSV", "Código seguro de verificación",
                             "Codi segur de verificació",
                             "Egiaztapen-kode segurua"],
        "organismo":        ["Ayuntamiento", "DGT",
                             "Jefatura Provincial de Tráfico",
                             "Policía Local",
                             "Ajuntament", "Guàrdia Urbana",
                             "Udala", "Udaltzaingoa",
                             "Concello"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 21. SANCIÓN URBANÍSTICA
    # ═══════════════════════════════════════════════════════════════════════
    "sancion_urbanistica": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Infractor", "Responsable",
                             "Interesado", "Promotor"],
        "domicilio":        ["Domicilio", "Dirección"],
        "expediente":       ["Expediente", "Nº expediente",
                             "Expediente sancionador", "Expediente de disciplina"],
        "infraccion":       ["Infracción urbanística", "Tipo de infracción",
                             "Hechos", "Precepto infringido", "Artículo",
                             "Norma infringida"],
        "ubicacion":        ["Ubicación", "Dirección de la obra",
                             "Emplazamiento", "Parcela", "Finca"],
        "gravedad":         ["Gravedad", "Leve", "Grave", "Muy grave"],
        "importe":          ["Importe", "Sanción", "Multa",
                             "Cuantía de la sanción"],
        "medida_cautelar":  ["Medida cautelar", "Suspensión de obras",
                             "Paralización", "Orden de demolición",
                             "Restauración de la legalidad"],
        "plazo":            ["Plazo", "Plazo de alegaciones",
                             "Plazo de recurso"],
        "fecha":            ["Fecha", "Fecha de la resolución",
                             "Fecha notificación"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "Concejalía de Urbanismo",
                             "Junta de Gobierno"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 22. SANCIÓN TRIBUTARIA
    # ═══════════════════════════════════════════════════════════════════════
    "sancion_tributaria": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Obligado tributario",
                             "Contribuyente", "Infractor"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "expediente":       ["Expediente", "Nº expediente",
                             "Expediente sancionador"],
        "tipo_infraccion":  ["Tipo de infracción", "Infracción tributaria",
                             "Leve", "Grave", "Muy grave",
                             "Art. 191", "Art. 192", "Art. 193",
                             "Art. 194", "Art. 195",
                             "No presentar declaración",
                             "Presentar declaración incorrecta"],
        "base_sancion":     ["Base de la sanción", "Perjuicio económico",
                             "Cantidad dejada de ingresar"],
        "porcentaje":       ["Porcentaje", "Graduación",
                             "Porcentaje de sanción", "Criterios de graduación"],
        "importe":          ["Importe", "Sanción", "Importe de la sanción",
                             "Cuantía de la sanción"],
        "reduccion":        ["Reducción", "Reducción por conformidad",
                             "Reducción por pronto pago",
                             "Reducción art. 188 LGT"],
        "total":            ["Total", "Total a ingresar"],
        "fecha":            ["Fecha", "Fecha de la resolución",
                             "Fecha emisión"],
        "periodo":          ["Período", "Ejercicio"],
        "concepto":         ["Concepto", "Tributo", "Impuesto"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Agencia Tributaria", "Ayuntamiento",
                             "Inspección tributaria"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 23. REQUERIMIENTO DE PAGO (todos los idiomas)
    # ═══════════════════════════════════════════════════════════════════════
    "requerimiento_pago": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "IFZ"],
        "nombre":           ["Nombre", "Contribuyente", "Deudor",
                             "Obligado al pago",
                             "Nom", "Contribuent", "Deutor",
                             "Izena", "Zergaduna", "Zorduna",
                             "Nome", "Debedor"],
        "domicilio":        ["Domicilio", "Domicilio fiscal",
                             "Domicili", "Adreça",
                             "Helbidea", "Enderezo"],
        "referencia":       ["Referencia", "Nº requerimiento", "Expediente",
                             "Referència", "Núm. requeriment",
                             "Erreferentzia", "Errekerimendu zk."],
        "concepto":         ["Concepto", "Deuda", "Tributo",
                             "Concepte", "Deute", "Tribut",
                             "Kontzeptua", "Zorra", "Zerga",
                             "Débeda"],
        "importe":          ["Importe", "Importe requerido",
                             "Deuda pendiente", "Principal",
                             "Import", "Import requerit", "Deute pendent",
                             "Zenbatekoa", "Eskatutako zenbatekoa",
                             "Débeda pendente"],
        "recargo":          ["Recargo", "Recargo de apremio",
                             "Recàrrec",
                             "Errekargua", "Recarga"],
        "intereses":        ["Intereses", "Intereses de demora",
                             "Interessos", "Interessos de demora",
                             "Interesak", "Berandutza-interesak",
                             "Xuros", "Xuros de demora"],
        "total":            ["Total", "Total a ingresar", "Importe total",
                             "Total a ingressar", "Import total",
                             "Guztira", "Guztira sartu beharrekoa"],
        "fecha":            ["Fecha", "Fecha del requerimiento",
                             "Data", "Data del requeriment",
                             "Errekerimenduaren data",
                             "Data do requirimento"],
        "plazo":            ["Plazo de pago", "Fecha límite",
                             "Termini de pagament", "Data límit",
                             "Ordainketa-epea", "Muga-data",
                             "Prazo de pagamento", "Data límite"],
        "consecuencias":    ["Consecuencias", "Apercibimiento",
                             "En caso de impago", "Advertencia",
                             "Conseqüències", "Advertiment",
                             "Ondorioak", "Ohartarazpena",
                             "Advertencia"],
        "cuenta":           ["Cuenta de ingreso", "IBAN",
                             "Compte d'ingrés",
                             "Sarrera-kontua",
                             "Conta de ingreso"],
        "csv":              ["CSV", "Código seguro de verificación",
                             "Codi segur de verificació",
                             "Egiaztapen-kode segurua"],
        "organismo":        ["Ayuntamiento", "Tesorería", "Recaudación",
                             "Ajuntament", "Tresoreria", "ORGT", "SUMA",
                             "Udala", "Diruzaintza", "Bilketa",
                             "Concello", "Tesouraría"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 24. REQUERIMIENTO DE INFORMACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    "requerimiento_informacion": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Obligado tributario",
                             "Requerido"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "referencia":       ["Referencia", "Nº requerimiento", "Expediente"],
        "tipo_requerimiento": ["Requerimiento de información",
                               "Art. 93 LGT", "Art. 94 LGT",
                               "Deber de información",
                               "Requerimiento individualizado",
                               "Captación de datos"],
        "informacion_solicitada": ["Información solicitada", "Se requiere",
                                    "Documentación", "Datos solicitados",
                                    "Aporte", "Justificantes"],
        "plazo":            ["Plazo", "Plazo de contestación",
                             "En el plazo de", "Diez días",
                             "Quince días"],
        "consecuencias":    ["Consecuencias del incumplimiento",
                             "Infracción", "Sanción por no atender"],
        "fecha":            ["Fecha", "Fecha emisión"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Agencia Tributaria", "Ayuntamiento",
                             "Inspección"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 25. NOTIFICACIÓN DEHú / DEH
    # ═══════════════════════════════════════════════════════════════════════
    "notificacion_dehu": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "Identificación"],
        "nombre":           ["Nombre", "Razón social", "Destinatario",
                             "Titular"],
        "organismo_emisor": ["Organismo emisor", "Remitente", "Emisor",
                             "Órgano emisor", "Entidad emisora"],
        "codigo_sie":       ["Código SIE", "Código DIR3", "SIE", "DIR3"],
        "asunto":           ["Asunto", "Concepto", "Materia",
                             "Descripción", "Tipo de envío"],
        "referencia":       ["Referencia", "Nº envío", "Identificador",
                             "Código de envío"],
        "fecha_puesta":     ["Fecha de puesta a disposición",
                             "Fecha puesta disposición",
                             "Fecha disponibilidad", "Puesto a disposición"],
        "fecha_acceso":     ["Fecha de acceso", "Fecha de lectura",
                             "Accedido", "Leído"],
        "fecha_rechazo":    ["Fecha de rechazo automático",
                             "Fecha rechazo", "Rechazado automáticamente",
                             "Expiración"],
        "estado":           ["Estado", "Estado de la notificación",
                             "Situación", "Pendiente", "Aceptada",
                             "Rechazada", "Expirada", "Notificada"],
        "procedimiento":    ["Procedimiento", "Tipo de procedimiento"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "num_notificacion": ["Nº de notificación", "Número de notificación",
                             "Identificador de notificación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 26. ACTA DE INSPECCIÓN
    # ═══════════════════════════════════════════════════════════════════════
    "acta_inspeccion": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Obligado tributario",
                             "Inspeccionado"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "referencia":       ["Nº acta", "Número de acta", "Referencia",
                             "Expediente", "Actuación"],
        "tipo_acta":        ["Tipo de acta", "Acta de conformidad",
                             "Acta de disconformidad", "Acta con acuerdo",
                             "Acta previa",
                             # CA
                             "Acta de conformitat", "Acta de disconformitat"],
        "concepto":         ["Concepto", "Tributo", "Impuesto inspeccionado"],
        "periodo":          ["Período", "Ejercicio comprobado",
                             "Períodos comprobados"],
        "base_regularizada":["Base regularizada", "Base imponible propuesta",
                             "Diferencia de base"],
        "cuota":            ["Cuota", "Cuota propuesta", "Deuda propuesta",
                             "Cuota diferencial"],
        "intereses":        ["Intereses", "Intereses de demora"],
        "sancion":          ["Sanción", "Importe sanción", "Sanción propuesta"],
        "total":            ["Total", "Deuda total", "Total propuesta"],
        "fecha":            ["Fecha", "Fecha del acta", "Fecha de la inspección"],
        "inspector":        ["Inspector", "Actuario", "Funcionario actuante"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Agencia Tributaria", "Ayuntamiento",
                             "Inspección tributaria",
                             "Agència Tributària de Catalunya"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 27. CARTA DE PAGO / AUTOLIQUIDACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    "carta_pago": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Contribuyente",
                             "Declarante",
                             "Nom", "Contribuent", "Declarant"],
        "domicilio":        ["Domicilio", "Domicili"],
        "referencia":       ["Referencia", "Nº autoliquidación",
                             "Carta de pago", "Justificante",
                             "Referència", "Carta de pagament"],
        "modelo":           ["Modelo", "Modelo tributario", "Mod.",
                             "Model"],
        "concepto":         ["Concepto", "Tributo", "Impuesto",
                             "ICIO", "Plusvalía", "IIVTNU",
                             "Impuesto sobre Construcciones",
                             "Concepte", "Tribut", "Impost"],
        "base":             ["Base imponible", "Base liquidable",
                             "Base imposable"],
        "tipo":             ["Tipo", "Tipo de gravamen",
                             "Tipus"],
        "cuota":            ["Cuota", "A ingresar", "Cuota tributaria",
                             "Quota"],
        "total":            ["Total", "Total a ingresar", "Importe",
                             "Total a ingressar", "Import"],
        "periodo":          ["Período", "Ejercicio",
                             "Període", "Exercici"],
        "fecha":            ["Fecha", "Fecha de presentación",
                             "Data", "Data de presentació"],
        "forma_pago":       ["Forma de pago", "Medio de pago",
                             "Domiciliación", "Efectivo", "Transferencia",
                             "Forma de pagament", "Domiciliació"],
        "cuenta":           ["Cuenta", "IBAN", "Entidad",
                             "Compte"],
        "csv":              ["CSV", "Código seguro de verificación",
                             "Codi segur de verificació"],
        "organismo":        ["Ayuntamiento", "Hacienda municipal",
                             "Ajuntament", "Hisenda municipal"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 28. CERTIFICADO ESTAR AL CORRIENTE
    # ═══════════════════════════════════════════════════════════════════════
    "certificado_corriente": {
        "nif":              ["NIF", "CIF", "NIF/CIF", "IFZ"],
        "nombre":           ["Nombre", "Razón social", "Titular",
                             "Nom", "Raó social",
                             "Izena", "Sozietatearen izena",
                             "Nome"],
        "tipo_certificado": ["Certificado de estar al corriente",
                             "Certificado de no deudor",
                             "Certificado negativo de deudas",
                             "Certificat d'estar al corrent",
                             "Certificat de no deutor",
                             "Egunean izateko ziurtagiria",
                             "Zordun ez izatearen ziurtagiria",
                             "Certificado de estar ao corrente",
                             "Certificado de non debedor"],
        "contenido":        ["Certifica que", "Se certifica", "Hace constar",
                             "Certifica que", "Es certifica", "Fa constar",
                             "Ziurtatzen du", "Ziurtatu egiten da",
                             "Certifícase", "Fai constar"],
        "situacion":        ["Al corriente", "Sin deudas", "No constan deudas",
                             "Al corrent", "Sense deutes",
                             "Egunean", "Zorrik gabe",
                             "Ao corrente", "Sen débedas"],
        "fecha_emision":    ["Fecha de emisión", "Emitido el",
                             "Data d'emissió", "Emès el",
                             "Jaulkipen-data", "Jaulkia",
                             "Data de emisión", "Emitido o"],
        "validez":          ["Válido hasta", "Validez", "Caducidad",
                             "Vàlid fins a", "Validesa", "Caducitat",
                             "Noiz arte balio duen", "Baliozkotasuna",
                             "Válido ata", "Caducidade"],
        "finalidad":        ["Finalidad", "Objeto", "Para",
                             "Finalitat", "Objecte", "Per a",
                             "Helburua", "Xedea",
                             "Finalidade", "Obxecto"],
        "csv":              ["CSV", "Código seguro de verificación",
                             "Codi segur de verificació",
                             "Egiaztapen-kode segurua"],
        "organismo":        ["Ayuntamiento", "AEAT", "Seguridad Social",
                             "Tesorería",
                             "Ajuntament", "ORGT",
                             "Udala", "Foru Aldundia",
                             "Concello", "Deputación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 29. CERTIFICADO DE DEUDAS
    # ═══════════════════════════════════════════════════════════════════════
    "certificado_deudas": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Titular"],
        "tipo_certificado": ["Certificado de deudas",
                             "Certificado de deudas pendientes",
                             "Certificado positivo de deudas",
                             "Certificat de deutes",
                             "Zerren ziurtagiria",
                             "Certificado de débedas"],
        "deudas":           ["Deudas", "Deudas pendientes", "Conceptos",
                             "Liquidaciones pendientes",
                             "Deutes", "Deutes pendents",
                             "Zorrak", "Zor-zerrendak",
                             "Débedas", "Débedas pendentes"],
        "importe_total":    ["Importe total", "Total deudas",
                             "Import total", "Total deutes",
                             "Guztizko zenbatekoa",
                             "Importe total débedas"],
        "fecha_emision":    ["Fecha de emisión", "Emitido el",
                             "Data d'emissió",
                             "Jaulkipen-data",
                             "Data de emisión"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "AEAT", "TGSS",
                             "Ajuntament", "Udala", "Concello"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 30. CERTIFICADO DE EMPADRONAMIENTO
    # ═══════════════════════════════════════════════════════════════════════
    "certificado_empadronamiento": {
        "nif":              ["NIF", "DNI", "NIE", "Documento de identidad",
                             "IFZ", "NAN"],
        "nombre":           ["Nombre", "Nombre y apellidos",
                             "Apellidos y nombre",
                             "Nom", "Nom i cognoms",
                             "Izena", "Izen-abizenak",
                             "Nome", "Nome e apelidos"],
        "fecha_nacimiento": ["Fecha de nacimiento", "F. nacimiento",
                             "Data de naixement",
                             "Jaiotze-data",
                             "Data de nacemento"],
        "nacionalidad":     ["Nacionalidad", "Nacionalitat",
                             "Nazionalitatea", "Nacionalidade"],
        "domicilio":        ["Domicilio", "Dirección", "Dirección de empadronamiento",
                             "Domicili", "Adreça",
                             "Helbidea",
                             "Enderezo"],
        "municipio":        ["Municipio", "Localidad", "Población",
                             "Municipi", "Localitat",
                             "Udalerria", "Herria",
                             "Municipio", "Localidade"],
        "fecha_alta":       ["Fecha de alta", "Alta en el padrón",
                             "Inscrito desde", "Fecha de inscripción",
                             "Data d'alta", "Alta al padró",
                             "Alta-data", "Erroldan alta",
                             "Data de alta", "Alta no padrón"],
        "tipo_certificado": ["Certificado de empadronamiento",
                             "Certificado de residencia",
                             "Volante de empadronamiento",
                             "Certificat d'empadronament",
                             "Certificat de residència",
                             "Volant d'empadronament",
                             "Errolda-ziurtagiria",
                             "Bizileku-ziurtagiria",
                             "Certificado de empadroamento",
                             "Certificado de residencia"],
        "convivientes":     ["Convivientes", "Personas inscritas",
                             "Unidad de convivencia",
                             "Convivents", "Persones inscrites",
                             "Bizikidetza-unitatea",
                             "Conviventes"],
        "fecha_emision":    ["Fecha de emisión", "Emitido el",
                             "Data d'emissió",
                             "Jaulkipen-data",
                             "Data de emisión"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "Secretaría",
                             "Ajuntament", "Secretaria",
                             "Udala", "Idazkaritza",
                             "Concello", "Secretaría"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 31. RESOLUCIÓN DE RECURSO DE REPOSICIÓN
    # ═══════════════════════════════════════════════════════════════════════
    "resolucion_recurso": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Recurrente", "Interesado",
                             "Obligado tributario"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "referencia":       ["Referencia", "Nº recurso", "Expediente",
                             "Nº expediente", "Recurso de reposición"],
        "acto_recurrido":   ["Acto recurrido", "Liquidación recurrida",
                             "Providencia recurrida", "Objeto del recurso"],
        "fallo":            ["Fallo", "Resuelve", "Se resuelve",
                             "Estimado", "Desestimado",
                             "Estimación parcial", "Inadmitido",
                             "Estimar", "Desestimar"],
        "motivos":          ["Motivos", "Fundamentos", "Consideraciones",
                             "Fundamentos de derecho"],
        "nuevo_importe":    ["Nuevo importe", "Importe resultante",
                             "Liquidación resultante"],
        "fecha":            ["Fecha", "Fecha de la resolución",
                             "Fecha de la notificación"],
        "plazo_recurso":    ["Plazo", "Plazo para recurrir",
                             "Reclamación económico-administrativa",
                             "Recurso contencioso-administrativo",
                             "Plazo de recurso"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "AEAT", "TEAR",
                             "Tribunal Económico-Administrativo"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 32. APLAZAMIENTO / FRACCIONAMIENTO
    # ═══════════════════════════════════════════════════════════════════════
    "aplazamiento_fraccionamiento": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Contribuyente",
                             "Solicitante"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "referencia":       ["Referencia", "Nº expediente",
                             "Expediente de aplazamiento",
                             "Expediente de fraccionamiento"],
        "deuda_origen":     ["Deuda origen", "Concepto", "Tributo",
                             "Liquidaciones aplazadas"],
        "importe_total":    ["Importe total", "Deuda total",
                             "Total aplazado/fraccionado"],
        "num_plazos":       ["Número de plazos", "Nº de plazos",
                             "Fracciones", "Nº fracciones",
                             "Periodicidad"],
        "importe_plazo":    ["Importe por plazo", "Cuota mensual",
                             "Importe de cada fracción"],
        "primer_plazo":     ["Primer plazo", "Fecha primer vencimiento",
                             "Fecha primera cuota"],
        "ultimo_plazo":     ["Último plazo", "Fecha último vencimiento"],
        "tipo_interes":     ["Tipo de interés", "Interés de demora",
                             "Interés legal"],
        "garantia":         ["Garantía", "Tipo de garantía", "Aval",
                             "Aval bancario", "Sin garantía",
                             "Dispensa de garantía"],
        "cuenta_domiciliacion": ["Cuenta de domiciliación", "IBAN",
                                  "Cuenta bancaria"],
        "estado":           ["Estado", "Concedido", "Denegado",
                             "Admitido a trámite"],
        "fecha":            ["Fecha", "Fecha de la resolución"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Ayuntamiento", "TGSS",
                             "Agencia Tributaria", "Recaudación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 33. NOTIFICACIÓN CATASTRAL
    # ═══════════════════════════════════════════════════════════════════════
    "notificacion_catastro": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Titular catastral", "Propietario",
                             "Sujeto pasivo"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "ref_catastral":    ["Referencia catastral", "Ref. catastral",
                             "RC", "Referencia"],
        "situacion":        ["Situación", "Dirección del inmueble",
                             "Localización", "Ubicación"],
        "clase":            ["Clase", "Urbana", "Rústica", "BICE"],
        "uso":              ["Uso", "Uso principal", "Destino"],
        "superficie":       ["Superficie", "Superficie construida",
                             "Superficie del suelo", "M²"],
        "valor_catastral":  ["Valor catastral", "Valor catastral total",
                             "Valor del suelo", "Valor de la construcción",
                             "Valor catastral anterior",
                             "Valor catastral nuevo"],
        "tipo_alteracion":  ["Tipo de alteración", "Causa",
                             "Alta", "Baja", "Modificación",
                             "Cambio de titularidad", "Obra nueva",
                             "Segregación", "Agrupación"],
        "fecha":            ["Fecha", "Fecha de la notificación",
                             "Fecha de efectos"],
        "plazo":            ["Plazo", "Plazo de recurso",
                             "Recurso de reposición"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Catastro", "Dirección General del Catastro",
                             "Gerencia del Catastro",
                             "Gerencia Regional del Catastro"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 34. ALTA / MODIFICACIÓN EN PADRÓN FISCAL
    # ═══════════════════════════════════════════════════════════════════════
    "alta_padron": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Contribuyente", "Sujeto pasivo",
                             "Titular"],
        "domicilio":        ["Domicilio", "Domicilio fiscal"],
        "concepto":         ["Concepto", "Tributo", "Padrón",
                             "IBI", "IVTM", "IAE", "Tasa"],
        "tipo_movimiento":  ["Tipo de movimiento", "Alta", "Baja",
                             "Modificación", "Variación",
                             "Alta en el padrón", "Baja en el padrón"],
        "objeto":           ["Objeto tributario", "Matrícula",
                             "Referencia catastral", "Situación"],
        "cuota":            ["Cuota", "Cuota estimada", "Importe estimado"],
        "periodo":          ["Período", "Ejercicio", "Desde", "Efectos"],
        "fecha":            ["Fecha", "Fecha del alta", "Fecha de la baja",
                             "Fecha de la modificación"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["Ayuntamiento", "Gestión Tributaria"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 35. COMPENSACIÓN DE DEUDAS
    # ═══════════════════════════════════════════════════════════════════════
    "compensacion_deudas": {
        "nif":              ["NIF", "CIF", "NIF/CIF"],
        "nombre":           ["Nombre", "Razón social", "Obligado tributario"],
        "referencia":       ["Referencia", "Expediente"],
        "deuda_compensada": ["Deuda compensada", "Concepto",
                             "Liquidación compensada"],
        "credito_compensado":["Crédito compensado", "Devolución",
                              "Devolución aplicada", "Crédito reconocido"],
        "importe_compensado":["Importe compensado", "Importe",
                              "Cantidad compensada"],
        "resto_deuda":      ["Resto de deuda", "Deuda pendiente",
                             "Importe pendiente"],
        "resto_credito":    ["Resto de crédito", "Crédito pendiente",
                             "Saldo a favor"],
        "fecha":            ["Fecha", "Fecha de la compensación",
                             "Fecha de la resolución"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Ayuntamiento", "Recaudación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 36. DECLARACIÓN DE RESPONSABILIDAD
    # ═══════════════════════════════════════════════════════════════════════
    "declaracion_responsable": {
        "nif_deudor":       ["NIF del deudor principal", "NIF deudor",
                             "Deudor principal"],
        "nif_responsable":  ["NIF del responsable", "NIF responsable",
                             "Responsable"],
        "nombre_deudor":    ["Nombre del deudor", "Deudor principal"],
        "nombre_responsable":["Nombre del responsable", "Responsable",
                              "Responsable solidario", "Responsable subsidiario"],
        "tipo_responsabilidad":["Tipo de responsabilidad",
                                "Responsabilidad solidaria",
                                "Responsabilidad subsidiaria",
                                "Art. 42 LGT", "Art. 43 LGT"],
        "referencia":       ["Referencia", "Expediente", "Nº expediente"],
        "deuda":            ["Deuda", "Importe", "Alcance de la responsabilidad",
                             "Deuda derivada"],
        "concepto":         ["Concepto", "Deuda origen"],
        "fecha":            ["Fecha", "Fecha de la declaración",
                             "Fecha emisión"],
        "plazo":            ["Plazo", "Plazo de alegaciones",
                             "Plazo de audiencia"],
        "csv":              ["CSV", "Código seguro de verificación"],
        "organismo":        ["AEAT", "Agencia Tributaria", "Ayuntamiento",
                             "Recaudación"],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # 37. GENÉRICO (fallback — todos los idiomas)
    # ═══════════════════════════════════════════════════════════════════════
    "_generico": {
        "nif":       ["NIF", "CIF", "NIF/CIF", "N.I.F", "DNI", "NIE",
                      "IFZ", "IFK", "NAN"],
        "nombre":    ["Nombre", "Razón social", "Denominación",
                      "Contribuyente", "Titular", "Obligado tributario",
                      "Nom", "Raó social", "Contribuent",
                      "Izena", "Izen-abizenak", "Zergaduna",
                      "Nome", "Contribuínte"],
        "domicilio": ["Domicilio", "Domicilio fiscal", "Dirección",
                      "Domicili", "Adreça",
                      "Helbidea",
                      "Enderezo"],
        "fecha":     ["Fecha", "Fecha emisión", "Fecha de la notificación",
                      "Data", "Data emissió", "Data d'emissió",
                      "Data", "Jaulkipen-data",
                      "Data emisión"],
        "importe":   ["Importe", "Total", "Importe total", "A ingresar",
                      "Import", "Total a ingressar",
                      "Zenbatekoa", "Guztira",
                      "Importe total"],
        "referencia":["Referencia", "Ref.", "Expediente", "Nº expediente",
                      "Nº liquidación",
                      "Referència", "Núm. expedient", "Núm. de rebut",
                      "Erreferentzia", "Espediente zk.",
                      "Referencia"],
        "concepto":  ["Concepto", "Tributo", "Descripción",
                      "Concepte", "Tribut",
                      "Kontzeptua", "Zerga"],
        "periodo":   ["Período", "Periodo", "Ejercicio",
                      "Període", "Exercici",
                      "Aldia", "Ekitaldia",
                      "Exercicio"],
        "csv":       ["CSV", "Código seguro de verificación",
                      "Codi segur de verificació",
                      "Egiaztapen-kode segurua",
                      "Código seguro"],
        "organismo": ["Ayuntamiento", "Diputación", "AEAT",
                      "Agencia Tributaria", "TGSS",
                      "Ajuntament", "Diputació", "ORGT", "SUMA",
                      "Udala", "Foru Aldundia",
                      "Concello", "Deputación"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════

# Mapeo provincia → idiomas cooficiales
PROVINCIA_IDIOMAS = {
    # Catalán
    "Barcelona": ["es", "ca"], "Girona": ["es", "ca"],
    "Lleida": ["es", "ca"], "Tarragona": ["es", "ca"],
    "Islas Baleares": ["es", "ca"],
    # Valenciano
    "Alicante": ["es", "va"], "Castellón": ["es", "va"],
    "Valencia": ["es", "va"],
    # Euskera
    "Álava": ["es", "eu"], "Guipúzcoa": ["es", "eu"],
    "Vizcaya": ["es", "eu"], "Navarra": ["es", "eu"],
    # Gallego
    "A Coruña": ["es", "gl"], "Lugo": ["es", "gl"],
    "Ourense": ["es", "gl"], "Pontevedra": ["es", "gl"],
}

# Organismos de recaudación por provincia
ORGANISMOS_RECAUDACION = {
    "Barcelona":    ["ORGT", "Ajuntament de Barcelona", "Diputació de Barcelona"],
    "Girona":       ["XALOC", "Diputació de Girona"],
    "Lleida":       ["BASE - Gestió d'Ingressos", "Diputació de Lleida"],
    "Tarragona":    ["BASE - Gestió d'Ingressos", "Diputació de Tarragona"],
    "Alicante":     ["SUMA Gestión Tributaria", "Diputación de Alicante"],
    "Castellón":    ["REGTSA", "Diputación de Castellón"],
    "Valencia":     ["OAGRTL", "Diputación de Valencia"],
    "Álava":        ["Diputación Foral de Álava / Arabako Foru Aldundia"],
    "Guipúzcoa":    ["Diputación Foral de Gipuzkoa / Gipuzkoako Foru Aldundia"],
    "Vizcaya":      ["Diputación Foral de Bizkaia / Bizkaiko Foru Aldundia"],
    "Navarra":      ["Hacienda Foral de Navarra / Nafarroako Foru Ogasuna"],
    "A Coruña":     ["Deputación da Coruña", "ORAL"],
    "Lugo":         ["Deputación de Lugo"],
    "Ourense":      ["Deputación de Ourense"],
    "Pontevedra":   ["Deputación de Pontevedra"],
    "Málaga":       ["Gestrisam"],
    "Sevilla":      ["OPAEF", "Diputación de Sevilla"],
    "Islas Baleares": ["ATIB"],
    "Madrid":       ["Agencia Tributaria de Madrid"],
    "Las Palmas":   ["Cabildo de Gran Canaria"],
    "Santa Cruz de Tenerife": ["Cabildo de Tenerife"],
}


if __name__ == "__main__":
    total_tipos = len(ETIQUETAS_POR_TIPO)
    total_campos = sum(len(v) for v in ETIQUETAS_POR_TIPO.values())
    total_keywords = sum(
        sum(len(vals) for vals in tipo.values())
        for tipo in ETIQUETAS_POR_TIPO.values()
    )
    print(f"Tipos de documento: {total_tipos}")
    print(f"Campos totales:     {total_campos}")
    print(f"Palabras clave:     {total_keywords}")
    print(f"\nTipos disponibles:")
    for k in ETIQUETAS_POR_TIPO:
        campos = len(ETIQUETAS_POR_TIPO[k])
        kws = sum(len(v) for v in ETIQUETAS_POR_TIPO[k].values())
        print(f"  {k:40s}  {campos:3d} campos  {kws:4d} keywords")
