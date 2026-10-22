"""Services: las reglas de negocio de las historias de usuario.

Un service no sabe nada de HTTP: recibe datos, aplica las reglas, usa los repositories y, si algo
no se cumple, lanza una excepción propia (el router la traduce a un código HTTP).
"""
