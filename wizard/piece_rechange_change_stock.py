# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class piece_rechange_change_stock(models.TransientModel):
	"""Changer stock pièce de rechange"""
	_name = "piece.rechange.change.stock"

	nouveau_qte = fields.Float('Nouvelle quantité en stock', required=True)

	@api.one
	def action_appliquer(self):
		for rec in self:
			if rec.nouveau_qte < 0:
				raise Warning(_('Erreur!'), 
							_('Quantité ne peut pas être négatif.'))
			if self._context.get('active_id', False):
				self.env['maintenance.piece'].browse(self._context.get('active_id', False)).write({'quantite_stock': rec.nouveau_qte})
