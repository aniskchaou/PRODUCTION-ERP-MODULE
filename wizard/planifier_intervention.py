# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class planifier_intervention(models.TransientModel):
	"""Planifier intervention"""
	_name = "planifier.intervention"

	type_prestataire = fields.Selection([('externe','Externe'),
										 ('interne','Interne')], 'Type prestataire', default='externe', required=True)
	prestataire_id = fields.Many2one('maintenance.prestataire', 'Prestataire', ondelete='cascade')
	operateur_id = fields.Many2one('production.operateur', 'Operateur', ondelete='cascade')
	date_entretien_planifie = fields.Datetime('Date entretien planifiée', required=True)

	@api.one
	def planifier_intervention(self):
		for data in self:
			if self._context.get('active_id', False):
				self.env['maintenance.demande.intervention'].browse(self._context.get('active_id', False)).write({'type_prestataire': data.type_prestataire, 'prestataire_id': data.prestataire_id.id, 'operateur_id': data.operateur_id.id, 'date_entretien_planifie': data.date_entretien_planifie, 'state': 'planifie'})

