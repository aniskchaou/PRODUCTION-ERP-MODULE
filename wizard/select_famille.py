# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class select_famille(models.TransientModel):
	"""Select famille"""
	_name = "select.famille"

	activite_famille_sortant_ids = fields.Many2many('production.famille', 'activite_famille_sortant_rel',
													'activite_id', 'famille_id', 'Familles sortantes')	



