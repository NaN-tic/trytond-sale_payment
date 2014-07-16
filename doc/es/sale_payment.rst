#:before:sale/sale:section:configuracion#

=============
Pago de venta
=============

Configuración
=============

Desde el menú Ventas/Configuración/Tiendas se definen las tiendas físicas donde
se harán los pagos de venta, indicando la secuencia de las ventas (pedidos), el
almacén desde donde se envían/reciben los productos y la tarifa, plazo de pago,
tercero por defecto y si se desea que por defecto se cree albarán para entregar
los productos vendidos en el domicilio del cliente, o éste se los lleva en el
momento de la venta.

Desde el menú Ventas/Configuración/Dispositivos se definen los dispositivos
físicos (terminales de venta) de cada tienda. Cada dispositivo tiene un nombre,
pertenece a una tienda y tiene asociados uno o varios diarios de extractos
contables (donde se anotarán los pagos). También se puede definir uno de estos
diarios de extractos que sea el usado por defecto en los pagos, normalmente el
más utilizado. Por ejemplo un dispositivo "TPV001" puede tener asociado los
diarios de extractos "Efectivo-TPV001" y "Tarjeta-TPV001". Y si és más habitual
recibir los pagos en efectivo, definir "Efectivo-TPV001" como el diario de
extractos por defecto.

Pagar una venta
===============

Mediante el botón "Pagar" se procede al pago total o parcial de una venta. En
una ventana emergente se pide el diario de extracto (forma de pago) y el importe
a pagar (por defecto el pendiente). Se puede realizar pagos parciales con la
misma o distintas formas de pago, por ejemplo sólo con Efectivo o con Efectivo y
Tarjeta. También se puede indicar un importe mayor que el de la venta, para que
aparezca un importe negativo indicando el cambio a devolver. Es importante que
se haya creado previamente un extracto bancario borrador donde anotar los pagos,
si no el programa nos avisará.

Si se realiza un pago parcial, se volverá a mostrar la ventana emergente con el
nuevo importe pendiente. Siempre se puede cancelar el nuevo pago, de forma que
la venta quedaría parcialmente pagada (por ejemplo cuando se hace una reserva
con una paga y señal).

Si se realiza un pago completo o el último pago parcial (el importe pendiente es
cero), la ventana emergente desaparece, la venta se confirma y se crean los
albaranes para el envío/recepción de productos y las facturas/abonos para la
contabilización de la venta. (todo: También se imprime el ticket de la venta TPV):

* Si la venta tiene sólo cantidades positivas, se crea un albarán de envío y
  una factura de cliente.
* Si la venta tiene sólo cantidades negativas (devolución), se crea un albarán
  de devolución y un abono de cliente.
* Si la venta tiene cantidades positivas y negativas, se crea ambos albaranes y
  facturas: Un albarán de envío y un albarán de devolución y una factura de
  cliente y un abono de cliente.

Las facturas/abonos quedan en estado confirmados (contabilizados), de forma que
es posible imprimir la factura en lugar del tiquet de la venta. Los albaranes
quedan confirmados, reservados y realizados, pues una venta implica que los
productos son transportados por el propio cliente en el momento de la venta.

Pueden consultarse los pagos y las facturas asociadas a la venta en las
pestañas "Pagos" y "Facturas". Los albaranes no son visibles desde las ventas
por no ser importantes (pueden ser consultados si se accede a las ventas
desde el menú Ventas/Ventas donde se ofrece una ficha completa de las mismas).

Estados
=======

Las ventas cambian entre los siguientes estados:

* Borrador a En proceso, cuando se paga completamente la venta.
* En proceo a Realizada, cuando se realiza el cierre de caja y las facturas
  asociadas a la venta TPV quedan pagadas.

Cuando se realiza la validación y confirmación de los extractos contables las
facturas asociadas quedan pagadas y las ventas realizadas. En algunos casos,
por ejemplo cuando existen pagos parciales negativos o ventas TPV con facturas y
abonos a la vez, las facturas no quedan pagadas automáticamente y hay que
ejecutar el asistente de cierre de ventas (todo) para que las facturas
queden pagadas y las ventas realizadas.

.. note::  Se generan albaranes sólo si hay al menos una línea del pedido de
           venta relacionada con un producto que sea de tipo Bienes.
