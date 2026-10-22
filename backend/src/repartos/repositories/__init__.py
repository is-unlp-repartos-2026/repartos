"""Consultas a la base de datos, escritas en SQL.

Todo el SQL del proyecto vive en esta carpeta, un archivo por tabla (por ejemplo, repartidores.py con
buscar_aptos(), insertar(), etc.). Los services llaman a estas funciones y nunca escriben SQL.

REGLA INNEGOCIABLE: los valores SIEMPRE van como parámetros, nunca armados con texto.

    Bien:   db.execute(text("SELECT * FROM repartidores WHERE dni = :dni"), {"dni": dni})
    Mal:    db.execute(text(f"SELECT * FROM repartidores WHERE dni = '{dni}'"))

Con el parámetro (:dni), PostgreSQL recibe la consulta y el valor por separado y nunca interpreta el valor
como SQL. Armando el texto, alguien puede mandar  ' OR '1'='1  como DNI y cambiar la consulta
(inyección SQL).
"""
