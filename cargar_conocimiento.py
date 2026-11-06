from db import conectar
import conocimiento

con = conectar(); cur = con.cursor(dictionary=True)
n = conocimiento.guardar(cur)
con.commit(); con.close()
print(f"Listo: {n} fragmentos guardados en conocimiento_plaga.")
