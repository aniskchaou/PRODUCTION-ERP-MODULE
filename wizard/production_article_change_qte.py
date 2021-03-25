# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class production_article_change_qte(models.TransientModel):
	"""Changer stock artices"""
	_name = "production.article.change.qte"

	nouveau_qte = fields.Float('Nouvelle quantité en stock', required=True)

	@api.one
	def change_product_qty(self):
		for data in self:
			if data.nouveau_qte < 0:
				raise Warning(_('Attention!'), 
							_('Quantité ne peut pas être négatif.'))
			if self._context.get('active_id', False):
				self.env['production.article'].browse(self._context.get('active_id', False)).write({'stock_reel': data.nouveau_qte})

