# -*- coding: utf-8 -*-

import sys
import openerp
from openerp import models, fields, api, _
from openerp import tools
from datetime import date
from datetime import datetime
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import re
import base64
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.modules.module import get_module_resource

#----------------------------------------------------------
# production_activite
#----------------------------------------------------------
class production_activite(models.Model):

    @api.one
    @api.depends('activite_famille_entrant_ids', 'activite_famille_sortant_ids')
    def _get_article_count(self):
        for activite in self:
            ids = []
#           for famille_entrant in activite.activite_famille_entrant_ids:
#               ids.append(famille_entrant.id)
            for famille_sortant in activite.activite_famille_sortant_ids:
                ids.append(famille_sortant.id)
            if ids:
                self.article_count = self.env['production.article'].search_count([('famille_id', 'in', tuple(ids))])

    @api.one
    @api.depends('activite_famille_entrant_ids', 'activite_famille_sortant_ids')
    def _get_machine_count(self):
        for activite in self:
            ids = []
#           for famille_entrant in activite.activite_famille_entrant_ids:
#               ids.append(famille_entrant.id)
            for famille_sortant in activite.activite_famille_sortant_ids:
                ids.append(famille_sortant.id)
            if ids:
                self.machine_count = self.env['production.machine'].search_count(['|','|','|',
                                                                                  ('famille_sortie1', 'in', tuple(ids)),
                                                                                  ('famille_sortie2', 'in', tuple(ids)),
                                                                                  ('famille_sortie3', 'in', tuple(ids)),
                                                                                  ('famille_sortie4', 'in', tuple(ids))])

    _name = 'production.activite'
    _rec_name = 'nom_activite'

    image = fields.Binary("Photo")
    image_medium = fields.Binary("Medium-sized image", compute='_compute_images', inverse='_inverse_image_medium', store=True)
    image_small = fields.Binary("Small-sized image", compute='_compute_images', inverse='_inverse_image_small', store=True)
    nom_activite = fields.Char('Activité :', required=True)
    activite_famille_entrant_ids = fields.Many2many('production.famille', 'activite_famille_entrant_rel',
                                                    'activite_id', 'famille_id', 'Familles entrantes')
    activite_famille_sortant_ids = fields.Many2many('production.famille', 'activite_famille_sortant_rel',
                                                    'activite_id', 'famille_id', 'Familles sortantes')
    #calculer le nombre d'articles pour chaque activite
    article_count = fields.Integer(compute='_get_article_count', string='Articles')
    #calculer le nombre de machines pour chaque activite
    machine_count = fields.Integer(compute='_get_machine_count', string='Machines')

    @api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

#   @api.multi
#   def ajouter_article(self):
#       return { 
#               'name': _("Article"),
#               'type': 'ir.actions.act_window',
#               'view_type': 'form',
#               'view_mode': 'form',
#               'res_model': 'production.article',
#               'view_id': False,
#               'context': {'default_activite_id': self.id},
#               }

    @api.multi
    def ajouter_article(self):
        for activite in self:
            ids = []
            article_ids = []
            for famille_sortant in activite.activite_famille_sortant_ids:
                ids.append(famille_sortant.id)
            if ids:
                article_objs = self.env['production.article'].search([('famille_id', 'in', tuple(ids))])

                for article in article_objs:
                    article_ids.append(article.id)
        return { 
                'name': _("Article"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'production.article',
                'target': 'current',
                'context': {'default_activite_id': self.id},
                'domain' : [('id','in',article_ids)],
                }

#   @api.multi
#   def ajouter_machine(self):
#       return { 
#               'name': _("Machine"),
#               'type': 'ir.actions.act_window',
#               'view_type': 'form',
#               'view_mode': 'form',
#               'res_model': 'production.machine',
#               'view_id': False,
#               'context': {'default_activite_id': self.id},
#               }

    @api.multi
    def ajouter_machine(self):
        for activite in self:
            ids = []
            machine_ids = []
            for famille_sortant in activite.activite_famille_sortant_ids:
                ids.append(famille_sortant.id)
            if ids:
                machine_objs = self.env['production.machine'].search(['|','|','|',
                                                                      ('famille_sortie1', 'in', tuple(ids)),
                                                                      ('famille_sortie2', 'in', tuple(ids)),
                                                                      ('famille_sortie3', 'in', tuple(ids)),
                                                                      ('famille_sortie4', 'in', tuple(ids))])
                for machine in machine_objs:
                    machine_ids.append(machine.id)
        return { 
                'name': _("Machine"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'production.machine',
                'target': 'current',
                'context': {'default_activite_id': self.id},
                'domain' : [('id','in',machine_ids)],
                }


#   @api.multi
#   def ajouter_OF(self):
#       return { 
#               'name': _("OF"),
#               'type': 'ir.actions.act_window',
#               'view_type': 'form',
#               'view_mode': 'form',
#               'res_model': 'production.ordre.fabrication',
#               'view_id': False,
#               'context': {'default_activite_id': self.id},
#               }



#----------------------------------------------------------
# production_article_machine_rel
#----------------------------------------------------------
class article_machine_rel(models.Model):

    @api.onchange('famille_id')
    def onchange_famille(self):
        #filter sur les machines selon la famille selectionné
        self.machine_id = []
        res = {}
        ids = []
        if self.famille_id:
            self.env.cr.execute('SELECT id FROM production_machine where %s IN \
                (famille_sortie1, famille_sortie2, famille_sortie3, famille_sortie4) ', (self.famille_id,))
            machine_objs = self.env.cr.fetchall()
            for m in machine_objs:
                ids.append(m)
        else:
            self.env.cr.execute('SELECT id FROM production_machine')
            machine_objs = self.env.cr.fetchall()
            for m in machine_objs:
                ids.append(m)
        res['domain'] = {'machine_id': [('id', 'in', ids)]}
        return res

    _name = "article.machine.rel"

    famille_id = fields.Integer('Famille')#champ pour filtrer les machines
    article_id = fields.Many2one('production.article', 'Article', ondelete='cascade')
    machine_id = fields.Many2one('production.machine', 'Machine', ondelete='cascade')
    cadence = fields.Float('Cadence (Unité/Heure)')

#----------------------------------------------------------
# production_operateur_machine_rel
#----------------------------------------------------------
class operateur_machine_rel(models.Model):
    _name = "operateur.machine.rel"

    operateur_id = fields.Many2one('production.operateur', 'Operateur', ondelete='cascade')
    machine_id = fields.Many2one('production.machine', 'Machine', ondelete='cascade')


#----------------------------------------------------------
# production_article
#----------------------------------------------------------
class production_article(models.Model):

    @api.onchange('famille_id')
    def onchange_famille(self):
        self.unite = self.famille_id.unite
        #si on change la famille on vide la liste des machines
        self.article_machine_ids = []

#   @api.onchange('activite_id')
#   def onchange_activite(self):
#       self.famille_id = []
#       res = {}
#       ids = []
#       if self.activite_id:
#           #on cherche les familles sortants de l'activité selectionné
#           for famille_sortant in self.activite_id.activite_famille_sortant_ids:
#               ids.append(famille_sortant.id)
#       else:
#           self.env.cr.execute('SELECT id FROM production_famille')
#           famille_objs = self.env.cr.fetchall()
#           for f in famille_objs:
#               ids.append(f)
#       res['domain'] = {'famille_id': [('id', 'in', ids)]}
#       return res

    @api.onchange('largeur','maille_transversal')
    def onchange_largeur_ou_mt(self):
        if self.largeur > 0 and self.maille_transversal > 0 :
            self.nbr_Barres_longitudinales = int(self.largeur / self.maille_transversal)

    @api.onchange('longueur','maille_longitudinal')
    def onchange_longueur_ou_ml(self):
        if self.longueur > 0 and self.maille_longitudinal > 0 :
            self.nbr_Barres_transversales = int(self.longueur / self.maille_longitudinal)

    @api.onchange('diametre','diametre_longitudinal','maille_transversal','maille_longitudinal','largeur','longueur',
                    'nbr_Barres_longitudinales','nbr_Barres_transversales')
    def onchange_fields_article(self):
        localdict = {
                    'd' : self.diametre,
                    'dl' : self.diametre_longitudinal,
                    'mt' : self.maille_transversal,
                    'ml' : self.maille_longitudinal,
                    'la' : self.largeur,
                    'lo' : self.longueur,
                    'nl' : self.nbr_Barres_longitudinales,
                    'nt' : self.nbr_Barres_transversales,
                    'pu' : self.poids_unit,
                    'mc' : self.dimension_m2,
                    'pl' : self.poids_lineaire,
                    }

        #calcul du Poids unit 
        if self.famille_id.calcul_poids:
            try:
                localdict['pu'] = eval(self.famille_id.calcul_poids, localdict)
                self.poids_unit = localdict.get("pu", None)
            except:
                pass

        #calcul du Dimension m² 
        if self.famille_id.calcul_surface:
            try:
                localdict['mc'] = eval(self.famille_id.calcul_surface, localdict)
                self.dimension_m2 = localdict.get("mc", None)
            except:
                pass

        #calcul du Poids linéaire
        if self.famille_id.calcul_poids_lineaire:
            try:
                localdict['pl'] = eval(self.famille_id.calcul_poids_lineaire, localdict)
                self.poids_lineaire = localdict.get("pl", None)
            except:
                pass

    @api.one
    @api.depends('stock_reel', 'stock_securite', 'stock_reserve')
    def _get_stock_disponible(self):
        self.stock_disponible = self.stock_reel - self.stock_securite - self.stock_reserve

    @api.one
    @api.depends('stock_reel', 'stock_reserve')
    def _get_stock_non_reserve(self):
        self.stock_non_reserve = self.stock_reel - self.stock_reserve


    _name = 'production.article'
    _rec_name = 'code_article'

#   activite_id = fields.Many2one('production.activite', 'Activité', ondelete='cascade')
    code_article = fields.Char('Code article', required=True)
    designation = fields.Char('Désignation', required=True)
    famille_id = fields.Many2one('production.famille', 'Famille', required=True, ondelete='RESTRICT')
    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], 'Unité par Default', required=True)
    diametre = fields.Float('Diamètre (mm)')
    transversal_ha = fields.Selection([('ha','HA')], 'Transversal HA')
    diametre_longitudinal = fields.Float('Diamètre longitudinal (mm)')
    longitudinal_ha = fields.Selection([('ha','HA')], 'Longitudinal HA')
    maille_transversal = fields.Float('Maille transversale')
    maille_longitudinal = fields.Float('Maille longitudinale')
    largeur = fields.Float('Largeur  (mm)')
    longueur = fields.Float('Longueur (mm)')
    poids_unit = fields.Float('Poids unitaire (Kg/U)', digits=(16,3))
    dimension_m2 = fields.Float('Surface m² (m²/U)', digits=(16,3))
    poids_lineaire = fields.Float('Poids linéaire (Kg/m)', digits=(16,3))
    article_machine_ids = fields.One2many('article.machine.rel', 'article_id', 'Machines')
    nbr_Barres_longitudinales = fields.Float('Nombre de barres longitudinales')
    nbr_Barres_transversales = fields.Float('Nombre de barres transversales')

    #stock
    # reel = disponible + securite + reserve
    # reel = reserve + non_reserve
    stock_reel = fields.Float('Stock réel', readonly="1")
    stock_securite = fields.Float('Stock sécurité')
    #stock_disponible = stock_reel - stock_securite - stock_reserve
    stock_disponible = fields.Float(compute='_get_stock_disponible', string='Stock disponible', readonly="1")
    stock_reserve = fields.Float('Stock réservé', readonly="1")
    #stock_non_reserve = stock_reel - stock_reserve
    stock_non_reserve = fields.Float(compute='_get_stock_non_reserve', string='Stock non réservé', readonly="1")
    stock_minimale = fields.Float('Stock minimale')
    stock_maximale = fields.Float('Stock maximale')

    famille_diametre = fields.Boolean(string='Diamètre', related='famille_id.diametre')
    famille_transversal_ha = fields.Boolean(string='Transversal HA', related='famille_id.transversal_ha')
    famille_diametre_longitudinal = fields.Boolean(string='Diamètre longitudinal', related='famille_id.diametre_longitudinal')
    famille_longitudinal_ha = fields.Boolean(string='Longitudinal HA', related='famille_id.longitudinal_ha')
    famille_maille_transversal = fields.Boolean(string='Maille transversale', related='famille_id.maille_transversal')
    famille_maille_longitudinal = fields.Boolean(string='Maille longitudinale', related='famille_id.maille_longitudinal')
    famille_largeur = fields.Boolean(string='Largeur', related='famille_id.largeur')
    famille_longueur = fields.Boolean(string='Longueur', related='famille_id.longueur')
    famille_poids_unit = fields.Boolean(string='Poids unitaire', related='famille_id.poids_unit')
    famille_dimension_m2 = fields.Boolean(string='Dimension m²', related='famille_id.dimension_m2')
    famille_poids_lineaire = fields.Boolean(string='Poids linéaire', related='famille_id.poids_lineaire')

    @api.model
    def create(self, values):
      
        #calcule nbr_Barres_longitudinales
        nbr_Barres_longitudinales = values.get('nbr_Barres_longitudinales', False)
        if nbr_Barres_longitudinales == False:
            largeur = values.get('largeur', False)
            maille_transversal = values.get('maille_transversal', False)
            if largeur and largeur > 0 and maille_transversal and maille_transversal > 0 :
                values['nbr_Barres_longitudinales'] = int(largeur / maille_transversal)

        #calcule nbr_Barres_transversales
        nbr_Barres_transversales = values.get('nbr_Barres_transversales', False)
        if nbr_Barres_transversales == False:
            longueur = values.get('longueur', False)
            maille_longitudinal = values.get('maille_longitudinal', False)
            if longueur and longueur > 0 and maille_longitudinal and maille_longitudinal > 0 :
                values['nbr_Barres_transversales'] = int(longueur / maille_longitudinal)

        #test code_article doit etre unique
        if self.env['production.article'].search_count([('code_article', '=', values['code_article'])]) > 0:
            raise Warning(_('Erreur!'), 
                        _('Code article existe déjà [ %s ].')% (values['code_article']))

        new_id = super(production_article, self).create(values)
        for obj in self.browse(new_id.id):
            localdict = {
                    'd' : obj.diametre,
                    'dl' : obj.diametre_longitudinal,
                    'mt' : obj.maille_transversal,
                    'ml' : obj.maille_longitudinal,
                    'la' : obj.largeur,
                    'lo' : obj.longueur,
                    'nl' : obj.nbr_Barres_longitudinales,
                    'nt' : obj.nbr_Barres_transversales,
                    'pu' : obj.poids_unit,
                    'mc' : obj.dimension_m2,
                    'pl' : obj.poids_lineaire,
                    }

            #calcul du Poids unit 
            if obj.poids_unit == 0 and obj.famille_id.calcul_poids:
                try:
                    localdict['pu'] = eval(obj.famille_id.calcul_poids, localdict)
                    obj.poids_unit = localdict.get("pu", 0)
                except:
                    pass

            #calcul du Dimension m² 
            if obj.dimension_m2 == 0 and obj.famille_id.calcul_surface:
                try:
                    localdict['mc'] = eval(obj.famille_id.calcul_surface, localdict)
                    obj.dimension_m2 = localdict.get("mc", 0)
                except:
                    pass

            #calcul du Poids linéaire
            if obj.poids_lineaire == 0 and obj.famille_id.calcul_poids_lineaire:
                try:
                    localdict['pl'] = eval(obj.famille_id.calcul_poids_lineaire, localdict)
                    obj.poids_lineaire = localdict.get("pl", 0)
                except:
                    pass

        return new_id

    @api.multi
    def write(self, values):
        obj_id=super(production_article, self).write(values)
        #test code_article doit etre unique
        if self.env['production.article'].search_count([('code_article', '=', self.code_article)]) > 1:
            raise Warning(_('Erreur!'), 
                        _('Code article existe déjà [ %s ].')% (self.code_article))

        return obj_id

    def notif(self, title, record_name, res_id, model, recepteur):
        mail_vals = {
                    'body': '<html>'+title+'</html>',
                    'record_name': record_name,
                    'res_id': res_id,
                    'reply_to': self.env['res.users'].browse(self.env.uid).name,
                    'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                    'model': model,
                    'type': 'email',
                    'email_from': self.env['res.users'].browse(self.env.uid).name,
                    'starred': True,
                    }
        message = self.env['mail.message'].create(mail_vals)

        mail_notif_vals = {
                        'partner_id': self.env['res.users'].browse(recepteur).partner_id.id,
                        'message_id': message.id,
                        'is_read': False,
                        'starred': True,
                        }
        self.env['mail.notification'].create(mail_notif_vals)

        return True

    def verifier_stock(self):
        #list des utilisateur du group production
        group = self.env['res.groups'].search([('name', '=', 'Groupe production')])
        for record in self:
            if record.stock_reel <= record.stock_minimale:
                for user in group.users:
                    title = 'Quantité stock minimale dépassé'
                    record_name = record.code_article
                    res_id = record.id
                    model = 'production.article'
                    recepteur = user.id
                    self.notif(title, record_name, res_id, model, recepteur)
            if record.stock_reel >= record.stock_maximale and record.stock_maximale != 0:
                for user in group.users:
                    title = 'Quantité stock maximale dépassé'
                    record_name = record.code_article
                    res_id = record.id
                    model = 'production.article'
                    recepteur = user.id
                    self.notif(title, record_name, res_id, model, recepteur)
        return True

    @api.multi
    def creer_of(self):

        return { 
            'name': _("Ordre fabrication"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'production.ordre.fabrication',
            'view_id': False,
            'context': {
                    'default_article_sortant': self.id,
                    },
            }

#   @api.multi
#   def creer_commande(self):
#       return { 
#               'name': _("Commande fournisseur"),
#               'type': 'ir.actions.act_window',
#               'view_type': 'form',
#               'view_mode': 'form',
#               'res_model': 'article.commande.fournisseur.rel',
#               'view_id': False,
#               'context': { 
#                           'default_article_id': self.id,
#                           },
#               }

    @api.multi
    def creer_demande(self):
        return { 
                'name': _("demande d'achat"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'demande.achat',
                'view_id': False,
                'context': { 
                            'default_article_id': self.id,
                            },
                }
#----------------------------------------------------------
# production_famille
#----------------------------------------------------------
class production_famille(models.Model):

    _name = 'production.famille'
    _rec_name = 'catdescription'

    image = fields.Binary("Photo")
    image_medium = fields.Binary("Medium-sized image", compute='_compute_images', inverse='_inverse_image_medium', store=True)
    image_small = fields.Binary("Small-sized image", compute='_compute_images', inverse='_inverse_image_small', store=True)
    article_ids = fields.One2many('production.article', 'famille_id', 'Article')
    categoryID = fields.Char('Code :',  readonly=True)
    catdescription = fields.Char('Nom', required=True)
    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], 'Unité par Default', required=True, default='kg')
    ###parametrage interface article
    #choix des champs actives
    all_ar = fields.Boolean('Tout')
    diametre = fields.Boolean('Diamètre (d)')
    transversal_ha = fields.Boolean('Transversal HA (tha)')
    diametre_longitudinal = fields.Boolean('Diamètre longitudinal (dl)')
    longitudinal_ha = fields.Boolean('Longitudinal HA (lha)')
    maille_transversal = fields.Boolean('Maille transversale (mt)')
    maille_longitudinal = fields.Boolean('Maille longitudinale (ml)')
    largeur = fields.Boolean('Largeur (la)')
    longueur = fields.Boolean('Longueur (lo)')
    poids_unit = fields.Boolean('Poids unitaire (pu)')
    dimension_m2 = fields.Boolean('Surface m² (mc)')
    poids_lineaire = fields.Boolean('Poids linéaire (pl)')
    #calcul du poids et surface
    calcul_poids = fields.Char('Calcul poids (Kg/U) =')
    calcul_surface = fields.Char('Calcul surface (m²/U) =')
    calcul_poids_lineaire = fields.Char('Calcul poids linéaire (Kg/m) =')

    ###parametrage interface OF
    #choix des champs actives
    all_of = fields.Boolean('Tout')
    article_entree2 = fields.Boolean('Article entrée2')
    tolerance_qte_plus = fields.Boolean('Tolérance qte plus')
    tolerance_qte_moins = fields.Boolean('Tolérance qte moins')
    tolerance_dimension = fields.Boolean('Tolérance dimension')
    #parametrage des familles entrants calcul q1 et q2 , ajout des condisions
    famille_entrant_param_ids = fields.One2many('production.famille.entrant.param', 'famille_sortant_id', 'Parametre')
    famille_entrant_param2_ids = fields.One2many('production.famille.entrant.param', 'famille_sortant_id', 'Parametre')


    @api.model
    def create(self, values):
        #generer code sequence "categoryID"
        values['categoryID'] = self.env['ir.sequence'].get('production.famille')

        return super(production_famille, self).create(values)

    @api.multi
    def write(self, values):
        obj_id=super(production_famille, self).write(values)
        for obj in self:
            #test unicite des lignes params
            list_famille = []
            if obj.article_entree2 == False:
                for param in obj.famille_entrant_param_ids:
                    if param.famille_entrant1_id.id in list_famille:
                        raise Warning(_('Erreur!'), 
                                    _('Famille existe 2 fois'))
                    list_famille.append(param.famille_entrant1_id.id)
            else:
                for param in obj.famille_entrant_param2_ids:
                    if (param.famille_entrant1_id.id, param.famille_entrant2_id.id) in list_famille:
                        raise Warning(_('Erreur!'), 
                                    _('Famille existe 2 fois'))
                    list_famille.append((param.famille_entrant1_id.id, param.famille_entrant2_id.id))
            #mise à jour poids_unit dimension_m2 poids_lineaire dans article
            for articles in self.env['production.article'].search([('famille_id', '=', obj.id)]):
                articles.onchange_fields_article()

        return obj_id

    @api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

    @api.onchange('all_ar')
    def onchange_all_ar(self):
        if self.all_ar == False:
            self.diametre = False   
            self.transversal_ha = False 
            self.diametre_longitudinal = False  
            self.longitudinal_ha = False    
            self.maille_transversal = False 
            self.maille_longitudinal = False    
            self.largeur = False    
            self.longueur = False   
            self.poids_unit = False 
            self.dimension_m2 = False   
            self.poids_lineaire = False 
        else:
            if self.all_ar == True:
                self.diametre = True    
                self.transversal_ha = True  
                self.diametre_longitudinal = True   
                self.longitudinal_ha = True 
                self.maille_transversal = True  
                self.maille_longitudinal = True 
                self.largeur = True 
                self.longueur = True    
                self.poids_unit = True  
                self.dimension_m2 = True    
                self.poids_lineaire = True  

    @api.onchange('all_of')
    def onchange_all_of(self):
        if self.all_of == False:
            self.article_entree2 = False
            self.tolerance_qte_plus = False
            self.tolerance_qte_moins = False
            self.tolerance_dimension = False
        else:
            if self.all_of == True:
                self.article_entree2 = True
                self.tolerance_qte_plus = True
                self.tolerance_qte_moins = True
                self.tolerance_dimension = True
#####

    @api.multi
    def ajouter_of(self):

        return { 
                'name': _("OF"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'production.ordre.fabrication',
                'view_id': False,
                'context': {'default_famille_id': self.id,},
                }

    @api.multi
    def ajouter_article(self):

        return { 
                'name': _("Article"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'production.article',
                'view_id': False,
                'context': {'default_famille_id': self.id,},
                }

#----------------------------------------------------------
# production_famille_entrant_param
#----------------------------------------------------------
class production_famille_entrant_param(models.Model):

    @api.model
    def _get_unite_sortant(self):
        if self.env.context.get('default_famille_sortant_id', False):
            obj = self.env['production.famille'].browse(self.env.context['default_famille_sortant_id'])
            return obj.unite
        return False

    _name = 'production.famille.entrant.param'

    famille_sortant_id = fields.Many2one('production.famille', 'Famille sortante', ondelete='cascade', 
                                            default= lambda self: self._context.get('famille_sortant_id', False))
    unite_sortant = fields.Selection([('u','U'),
                                      ('kg','Kg'),
                                      ('m2','m²'),
                                      ('m','m')], related='famille_sortant_id.unite')
    unite_qs = fields.Selection([('u','U'),
                                 ('kg','Kg'),
                                 ('m2','m²'),
                                 ('m','m')], 'Quantité sortante (qs) ', default=_get_unite_sortant)
    famille_entrant1_id = fields.Many2one('production.famille', 'Famille entrante1', ondelete='cascade')
    unite_entrant1 = fields.Selection([('u','U'),
                                       ('kg','Kg'),
                                       ('m2','m²'),
                                       ('m','m')], related='famille_entrant1_id.unite')
    famille_entrant2_id = fields.Many2one('production.famille', 'Famille entrante2', ondelete='cascade')
    unite_entrant2 = fields.Selection([('u','U'),
                                       ('kg','Kg'),
                                       ('m2','m²'),
                                       ('m','m')], related='famille_entrant2_id.unite')
    calcul_quantite1 = fields.Char('Calcul quantité1')
    unite_q1 = fields.Selection([('u','U'),
                                 ('kg','Kg'),
                                 ('m2','m²'),
                                 ('m','m')], 'Quantité entrante1 (q1) ')
    calcul_quantite2 = fields.Char('Calcul quantité2')
    unite_q2 = fields.Selection([('u','U'),
                                 ('kg','Kg'),
                                 ('m2','m²'),
                                 ('m','m')], 'Quantité entrante2 (q2) ')

    production_condition_ids = fields.One2many('production.condition', 'param_id', 'Conditions')
    #field boolean for 2eme article entrant
    entree2 = fields.Boolean('Article entrée2', related='famille_sortant_id.article_entree2')
    #field boolean for famille sortant
    diametre = fields.Boolean('Diamètre (d)', related='famille_sortant_id.diametre')
    transversal_ha = fields.Boolean('Transversal HA', related='famille_sortant_id.transversal_ha')
    diametre_longitudinal = fields.Boolean('Diamètre longitudinal (dl)', related='famille_sortant_id.diametre_longitudinal')
    longitudinal_ha = fields.Boolean('Longitudinal HA', related='famille_sortant_id.longitudinal_ha')
    maille_transversal = fields.Boolean('Maille transversale (mt)', related='famille_sortant_id.maille_transversal')
    maille_longitudinal = fields.Boolean('Maille longitudinale (ml)', related='famille_sortant_id.maille_longitudinal')
    largeur = fields.Boolean('Largeur (la)', related='famille_sortant_id.largeur')
    longueur = fields.Boolean('Longueur (lo)', related='famille_sortant_id.longueur')
    poids_unit = fields.Boolean('Poids unitaire (pu)', related='famille_sortant_id.poids_unit')
    dimension_m2 = fields.Boolean('Surface m² (mc)', related='famille_sortant_id.dimension_m2')
    poids_lineaire = fields.Boolean('Poids linéaire (pl)', related='famille_sortant_id.poids_lineaire')
    #field boolean for famille entrant1
    diametre1 = fields.Boolean('Diamètre (d)', related='famille_entrant1_id.diametre')
    transversal_ha1 = fields.Boolean('Transversal HA', related='famille_entrant1_id.transversal_ha')
    diametre_longitudinal1 = fields.Boolean('Diamètre longitudinal (dl)', related='famille_entrant1_id.diametre_longitudinal')
    longitudinal_ha1 = fields.Boolean('Longitudinal HA', related='famille_entrant1_id.longitudinal_ha')
    maille_transversal1 = fields.Boolean('Maille transversale (mt)', related='famille_entrant1_id.maille_transversal')
    maille_longitudinal1 = fields.Boolean('Maille longitudinale (ml)', related='famille_entrant1_id.maille_longitudinal')
    largeur1 = fields.Boolean('Largeur (la)', related='famille_entrant1_id.largeur')
    longueur1 = fields.Boolean('Longueur (lo)', related='famille_entrant1_id.longueur')
    poids_unit1 = fields.Boolean('Poids unitaire (pu)', related='famille_entrant1_id.poids_unit')
    dimension_m21 = fields.Boolean('Surface m² (mc)', related='famille_entrant1_id.dimension_m2')
    poids_lineaire1 = fields.Boolean('Poids linéaire (pl)', related='famille_entrant1_id.poids_lineaire')
    #field boolean for famille entrant2
    diametre2 = fields.Boolean('Diamètre (d)', related='famille_entrant2_id.diametre')
    transversal_ha2 = fields.Boolean('Transversal HA', related='famille_entrant2_id.transversal_ha')
    diametre_longitudinal2 = fields.Boolean('Diamètre longitudinal (dl)', related='famille_entrant2_id.diametre_longitudinal')
    longitudinal_ha2 = fields.Boolean('Longitudinal HA', related='famille_entrant2_id.longitudinal_ha')
    maille_transversal2 = fields.Boolean('Maille transversale (mt)', related='famille_entrant2_id.maille_transversal')
    maille_longitudinal2 = fields.Boolean('Maille longitudinale (ml)', related='famille_entrant2_id.maille_longitudinal')
    largeur2 = fields.Boolean('Largeur (la)', related='famille_entrant2_id.largeur')
    longueur2 = fields.Boolean('Longueur (lo)', related='famille_entrant2_id.longueur')
    poids_unit2 = fields.Boolean('Poids unitaire (pu)', related='famille_entrant2_id.poids_unit')
    dimension_m22 = fields.Boolean('Surface m² (mc)', related='famille_entrant2_id.dimension_m2')
    poids_lineaire2 = fields.Boolean('Poids linéaire (pl)', related='famille_entrant2_id.poids_lineaire')

    @api.onchange('famille_sortant_id')
    def onchange_famille_sortant(self):
        #filter sur le champ Famille entrant1 et Famille entrant2
        self.famille_entrant1_id = []
        self.famille_entrant2_id = []
        res = {}
        a_ids = []
        ids = []
        if self._context.get('default_famille_sortant_id', False):
            self.env.cr.execute('SELECT activite_id FROM activite_famille_sortant_rel where famille_id = %s', 
                                (self._context.get('default_famille_sortant_id', False),))
            activite_ids = self.env.cr.fetchall()
            for a in activite_ids:
                a_ids.append(a)
            if a_ids:
                self.env.cr.execute('SELECT famille_id FROM activite_famille_entrant_rel where activite_id IN %s', 
                                    (tuple(a_ids),))
                famille_ids = self.env.cr.fetchall()
                for f in famille_ids:
                    ids.append(f)
        res['domain'] = {
                        'famille_entrant1_id': [('id', 'in', ids)],
                        'famille_entrant2_id': [('id', 'in', ids)]
                        }
        return res

    @api.onchange('famille_entrant1_id')
    def onchange_famille_entrant1_id(self):
        self.unite_q1 = self.famille_entrant1_id.unite

    @api.onchange('famille_entrant2_id')
    def onchange_famille_entrant2_id(self):
        self.unite_q2 = self.famille_entrant2_id.unite

    @api.multi
    def validate_formule(self, formule):
        if formule == "qs":
            return True
        return False

    @api.multi
    def test_formule(self, formule, values):
        localdict = {}
        localdict['qs'] = 1
        localdict['q1'] = 1
        localdict['q2'] = 1

        if values.get("diametre", None) == True or self.diametre == True: 
            localdict['d'] = 1
        if values.get("diametre_longitudinal", None) == True or self.diametre_longitudinal == True:
            localdict['dl'] = 1
        if values.get("maille_transversal", None) == True or self.maille_transversal == True:
            localdict['mt'] = 1
        if values.get("maille_longitudinal", None) == True or self.maille_longitudinal == True:
            localdict['ml'] = 1
        if values.get("largeur", None) == True or self.largeur == True:
            localdict['la'] = 1
        if values.get("longueur", None) == True or self.longueur == True:
            localdict['lo'] = 1
        if values.get("largeur", None) == True and values.get("maille_transversal", None) == True  or self.largeur == True and self.maille_transversal == True:
            localdict['nl'] = 1
        if values.get("longueur", None) == True and values.get("maille_longitudinal", None) == True or self.longueur == True and self.maille_longitudinal == True:
            localdict['nt'] = 1
        if values.get("poids_unit", None) == True or self.poids_unit == True:
            localdict['pu'] = 1
        if values.get("dimension_m2", None) == True or self.dimension_m2 == True:
            localdict['mc'] = 1
        if values.get("poids_lineaire", None) == True or self.poids_lineaire == True:
            localdict['pl'] = 1

        if values.get("poids_unit1", None) == True or self.poids_unit1 == True:
            localdict['pu1'] = 1
        if values.get("dimension_m21", None) == True or self.dimension_m21 == True:
            localdict['mc1'] = 1
        if values.get("poids_lineaire1", None) == True or self.poids_lineaire1 == True:
            localdict['pl1'] = 1
        if values.get("diametre1", None) == True or self.diametre1 == True:
            localdict['d1'] = 1
        if values.get("diametre_longitudinal1", None) == True or self.diametre_longitudinal1 == True:
            localdict['dl1'] = 1
        if values.get("maille_transversal1", None) == True or self.maille_transversal1 == True:
            localdict['mt1'] = 1
        if values.get("maille_longitudinal1", None) == True or self.maille_longitudinal1 == True:
            localdict['ml1'] = 1
        if values.get("largeur1", None) == True or self.largeur1 == True:
            localdict['la1'] = 1
        if values.get("longueur1", None) == True or self.longueur1 == True:
            localdict['lo1'] = 1
        if values.get("largeur1", None) == True and values.get("maille_transversal1", None) == True or self.largeur1 == True and self.maille_transversal1 == True:
            localdict['nl1'] = 1
        if values.get("longueur1", None) == True and values.get("maille_longitudinal1", None) == True or self.longueur1 == True and self.maille_longitudinal1 == True:
            localdict['nt1'] = 1

        if values.get("poids_unit2", None) == True or self.poids_unit2 == True:
            localdict['pu2'] = 1
        if values.get("dimension_m22", None) == True or self.dimension_m22 == True:
            localdict['mc2'] = 1
        if values.get("poids_lineaire2", None) == True or self.poids_lineaire2 == True:
            localdict['pl2'] = 1
        if values.get("diametre2", None) == True or self.diametre2 == True:
            localdict['d2'] = 1
        if values.get("diametre_longitudinal2", None) == True or self.diametre_longitudinal2 == True:
            localdict['dl2'] = 1
        if values.get("maille_transversal2", None) == True or self.maille_transversal2 == True:
            localdict['mt2'] = 1
        if values.get("maille_longitudinal2", None) == True or self.maille_longitudinal2 == True:
            localdict['ml2'] = 1
        if values.get("largeur2", None) == True or self.largeur2 == True:
            localdict['la2'] = 1
        if values.get("longueur2", None) == True or self.longueur2 == True:
            localdict['lo2'] = 1
        if values.get("largeur2", None) == True and values.get("maille_transversal2", None) == True or self.largeur2 == True and self.maille_transversal2 == True:
            localdict['nl2'] = 1
        if values.get("longueur2", None) == True and values.get("maille_longitudinal2", None) == True or self.longueur2 == True  and self.maille_longitudinal2 == True:
            localdict['nt2'] = 1

        try:
            eval(formule, localdict)
            return True
        except:
            return False

    @api.model
    def create(self, values):
        #test formule1
        formule1 = values.get("calcul_quantite1", None)
        if formule1:
            if self.test_formule(formule1, values) == False:
                raise osv.except_osv(_('Erreur!'), _('Formule invalide [ %s ].')% (formule1))

        #test conditions
        conditions = values.get("production_condition_ids", None)
        for line in conditions:
            if line[2]:
                condition = line[2].get("condition", None)
                if condition:
                    if self.test_formule(condition, values) == False:
                        raise Warning(_('Erreur!'), 
                                    _('Condition invalide [ %s ].')% (condition))


        #test formule2
        formule2 = values.get("calcul_quantite2", None)
        if formule2:
            if self.test_formule(formule2, values) == False:
                raise Warning(_('Erreur!'), 
                            _('Formule invalide [ %s ].')% (formule2))

        obj_id = super(production_famille_entrant_param, self).create(values)

        return obj_id

    @api.multi
    def write(self,values):
        #test formule1
        formule1 = values.get("calcul_quantite1", None)
        if formule1:
            if self.test_formule(formule1, values) == False:
                raise Warning(_('Erreur!'), 
                            _('Formule invalide [ %s ].')% (formule1))

        #test conditions
        conditions = values.get("production_condition_ids", None)
        if conditions:
            for line in conditions:
                if line[2]:
                    condition = line[2].get("condition", None)
                    if condition:
                        if self.test_formule(condition, values) == False:
                            raise Warning(_('Erreur!'), 
                                        _('Condition invalide [ %s ].')% (condition))

        #test formule2
        formule2 = values.get("calcul_quantite2", None)
        if formule2:
            if self.test_formule(formule2, values) == False:
                raise Warning(_('Erreur!'), 
                            _('Formule invalide [ %s ].')% (formule2))

        obj_id = super(production_famille_entrant_param, self).write(values)
        return obj_id

#----------------------------------------------------------
# production_condition
#----------------------------------------------------------
class production_condition(models.Model):

    _name = 'production.condition'

    param_id = fields.Many2one('production.famille.entrant.param', 'Parametre', ondelete='cascade')
    condition = fields.Char('Condition', required=True)

    entree2 = fields.Boolean('Article entrée2')
    #field boolean for famille sortant
    diametre = fields.Boolean('Diamètre (d)')
    transversal_ha = fields.Boolean('Transversal HA')
    diametre_longitudinal = fields.Boolean('Diamètre longitudinal (dl)')
    longitudinal_ha = fields.Boolean('Longitudinal HA')
    maille_transversal = fields.Boolean('Maille transversale (mt)')
    maille_longitudinal = fields.Boolean('Maille longitudinale (ml)')
    largeur = fields.Boolean('Largeur (la)')
    longueur = fields.Boolean('Longueur (lo)')
    poids_unit = fields.Boolean('Poids unitaire (pu)')
    dimension_m2 = fields.Boolean('Surface m² (mc)')
    poids_lineaire = fields.Boolean('Poids linéaire (pl)')
    #field boolean for famille entrant1
    diametre1 = fields.Boolean('Diamètre (d)')
    transversal_ha1 = fields.Boolean('Transversal HA')
    diametre_longitudinal1 = fields.Boolean('Diamètre longitudinal (dl)')
    longitudinal_ha1 = fields.Boolean('Longitudinal HA')
    maille_transversal1 = fields.Boolean('Maille transversale (mt)')
    maille_longitudinal1 = fields.Boolean('Maille longitudinale (ml)')
    largeur1 = fields.Boolean('Largeur (la)')
    longueur1 = fields.Boolean('Longueur (lo)')
    poids_unit1 = fields.Boolean('Poids unitaire (pu)')
    dimension_m21 = fields.Boolean('Surface m² (mc)')
    poids_lineaire1 = fields.Boolean('Poids linéaire (pl)')
    #field boolean for famille entrant2
    diametre2 = fields.Boolean('Diamètre (d)')
    transversal_ha2 = fields.Boolean('Transversal HA')
    diametre_longitudinal2 = fields.Boolean('Diamètre longitudinal (dl)')
    longitudinal_ha2 = fields.Boolean('Longitudinal HA')
    maille_transversal2 = fields.Boolean('Maille transversale (mt)')
    maille_longitudinal2 = fields.Boolean('Maille longitudinale (ml)')
    largeur2 = fields.Boolean('Largeur (la)')
    longueur2 = fields.Boolean('Longueur (lo)')
    poids_unit2 = fields.Boolean('Poids unitaire (pu)')
    dimension_m22 = fields.Boolean('Surface m² (mc)')
    poids_lineaire2 = fields.Boolean('Poids linéaire (pl)')

#----------------------------------------------------------
# production_operateur
#----------------------------------------------------------
class production_operateur(models.Model):

    @api.multi
    @api.depends('prenom', 'nom', 'code_operateur')
    def name_get(self):
        result = []
        for record in self:
#           result.append((record.id, record.prenom + ' ' + record.nom + ' (' + record.code_operateur +')'))
            note_moyenne = str(record.note_moyenne) if record.note_moyenne != False else ''
            result.append((record.id, record.prenom + ' ' + record.nom + ' ( ' + note_moyenne +' /20)'))
        return result

    @api.one
    def _get_note_moyenne(self):
        total = 0.0
        con = 0.0
        for m in self:
            for e in m.evaluation_ids:
                if e.qualite_service == "0":
                    total += 0
                elif e.qualite_service == "1":
                    total += 5
                elif e.qualite_service == "2":
                    total += 10
                elif e.qualite_service == "3":
                    total += 15
                elif e.qualite_service == "4":
                    total += 20
                else:
                    total += 0
                con += 1

        if con > 0:
            self.note_moyenne = total / con

    _name = 'production.operateur'

    image = fields.Binary("Image")
    image_medium = fields.Binary("Medium-sized image", compute='_compute_images', inverse='_inverse_image_medium', store=True)
    image_small = fields.Binary("Small-sized image", compute='_compute_images', inverse='_inverse_image_small', store=True)
    code_operateur = fields.Char('Code opérateur :', required=True)
    nom = fields.Char('Nom', required=True)
    prenom = fields.Char('Prénom', required=True)
    operateur_machine_ids = fields.Many2many('production.machine', 'operateur_machine_rel', 'operateur_id', 'machine_id',
                                                'Qualifié pour les machines')
    tel = fields.Char('Téléphone')
    email = fields.Char('Email')
    active = fields.Boolean('Actif', default=True)

    #coût horaire visible que par admin
    cout_horaire = fields.Float('Coût horaire')
    evaluation_ids = fields.One2many('maintenance.evaluation.operateur', 'production_operateur_id', 'Evaluations')
    note_moyenne = fields.Float(compute='_get_note_moyenne', string="Note moyenne", digits=(16,1))

    @api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

    @api.model
    def create(self, values):
        #test code_operateur doit etre unique
        if self.env['production.operateur'].search_count([('code_operateur', '=', values['code_operateur'])]) > 0:
            raise Warning(_('Erreur!'), 
                        _('Code operateur existe déjà [ %s ].')% (values['code_operateur']))
        new_id = super(production_operateur, self).create(values)
        return new_id

    @api.multi
    def write(self, values):
        obj_id=super(production_operateur,self).write(values)
        #test code_operateur doit etre unique
        if self.env['production.operateur'].search_count([('code_operateur', '=', self.code_operateur)]) > 1:
            raise Warning(_('Erreur!'), 
                        _('Code operateur existe déjà [ %s ].')% (self.code_operateur))
        return obj_id

#----------------------------------------------------------
# production_machine
#----------------------------------------------------------
class production_machine(models.Model):

    @api.multi
    @api.depends('nom', 'code_machine')
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.nom + ' (' + record.code_machine + ')'))
        return result

    @api.onchange('activite_id')
    def onchange_activite(self):
        self.famille_id = []
        res = {}
        ids_entrant = []
        ids_sortant = []
        if self.activite_id:
            for famille_sortant in self.activite_id.activite_famille_sortant_ids:
                ids_sortant.append(famille_sortant.id)
            for famille_entrant in self.activite_id.activite_famille_entrant_ids:
                ids_entrant.append(famille_entrant.id)
        else:
            self.env.cr.execute('SELECT id FROM production_famille')
            famille_objs = self.env.cr.fetchall()
            for f in famille_objs:
                ids_entrant.append(f)
                ids_sortant.append(f)
        res['domain'] = {
                        'famille_entree1': [('id', 'in', ids_entrant)],
                        'famille_entree2': [('id', 'in', ids_entrant)],
                        'famille_entree3': [('id', 'in', ids_entrant)],
                        'famille_entree4': [('id', 'in', ids_entrant)],
                        'famille_sortie1': [('id', 'in', ids_sortant)],
                        'famille_sortie2': [('id', 'in', ids_sortant)],
                        'famille_sortie3': [('id', 'in', ids_sortant)],
                        'famille_sortie4': [('id', 'in', ids_sortant)]
                        }
        return res

    @api.one
    def _get_duree_fonctionnement(self):
        duree = 0
        for m in self:
            for of in self.env['production.ordre.fabrication'].search([('code_machine', '=', m.id)]):
                for bef in of.bon_entree_fabrication_ids:
                    duree += bef.duree
        self.duree_fonctionnement = duree

    #calcul temp d'arrêt par machine
    @api.one
    def _get_temp_arret(self):
        temp = 0

        for m in self:
            for di in self.env['maintenance.demande.intervention'].search([('machine_id', '=', m.id)]):
                temp += di.temp_arret
        self.temp_arret = temp

    @api.one
    def _get_piece_count(self):
        for m in self:
            self.piece_count  = self.env['machine.piece.rel'].search_count([('machine_id', '=', m.id)])

    @api.one
    def _get_demande_intervention_count(self):
        for m in self:
            self.demande_intervention_count  = self.env['maintenance.demande.intervention'].search_count([('machine_id', '=', m.id)])

    @api.one
    def _get_maintenance_preventive_count(self):
        for m in self:
            self.maintenance_preventive_count  = self.env['maintenance.preventive'].search_count([('machine_id', '=', m.id)])

    _name = 'production.machine'

    image = fields.Binary("Photo")
    image_medium = fields.Binary("Medium-sized image", compute='_compute_images', inverse='_inverse_image_medium', store=True)
    image_small = fields.Binary("Small-sized image", compute='_compute_images', inverse='_inverse_image_small', store=True)
    activite_id = fields.Many2one('production.activite', 'Activité', ondelete='cascade')
    code_machine = fields.Char('Code', required=True)
    nom = fields.Char('Nom', required=True)
    annee_debut_production = fields.Selection([(num, str(num)) for num in range(1990, (datetime.now().year)+1 )], 'Année',      
                                                default= lambda *a:datetime.now().year)
    famille_entree1 = fields.Many2one('production.famille', 'Famille entrée1', ondelete='cascade')
    famille_entree2 = fields.Many2one('production.famille', 'Famille entrée2', ondelete='cascade')
    famille_entree3 = fields.Many2one('production.famille', 'Famille entrée3', ondelete='cascade')
    famille_entree4 = fields.Many2one('production.famille', 'Famille entrée4', ondelete='cascade')
    famille_sortie1 = fields.Many2one('production.famille', 'Famille sortie1', ondelete='cascade')
    famille_sortie2 = fields.Many2one('production.famille', 'Famille sortie2', ondelete='cascade')
    famille_sortie3 = fields.Many2one('production.famille', 'Famille sortie3', ondelete='cascade')
    famille_sortie4 = fields.Many2one('production.famille', 'Famille sortie4', ondelete='cascade')
    active = fields.Boolean('Active', default=True)

    duree_fonctionnement = fields.Float(compute='_get_duree_fonctionnement', string="Durée de fonctionnement")
    temp_arret = fields.Float(compute='_get_temp_arret', string="Temp d'arrêt")

    machine_piece_ids = fields.Many2many('maintenance.piece', 'machine_piece_rel', 'machine_id', 'piece_id', 'Piéces')
    demande_intervention_ids = fields.One2many('maintenance.demande.intervention', 'machine_id', 'Interventions')
    maintenance_preventive_ids = fields.One2many('maintenance.preventive', 'machine_id', 'Maintenance préventive')

    piece_count = fields.Integer(compute='_get_piece_count', string='Pièces')
    demande_intervention_count = fields.Integer(compute='_get_demande_intervention_count', string='Interventions')
    maintenance_preventive_count = fields.Integer(compute='_get_maintenance_preventive_count', string='M.P')

    operateur_machine_ids = fields.Many2many('production.operateur', 'operateur_machine_rel', 'machine_id', 'operateur_id',
                                                'Qualifié pour les machines')
    @api.model
    def create(self, values):
        #test code_machine doit etre unique
        if self.env['production.machine'].search_count([('code_machine', '=', values['code_machine'])]) > 0:
            raise Warning(_('Erreur!'), 
                        _('Code machine existe déjà [ %s ].')% (values['code_machine']))
        new_id = super(production_machine, self).create(values)
        #vals{'':}
        #self.pool.get('production.machine').create(values)
        return new_id
   
    @api.multi
    def write(self, values):
        obj_id=super(production_machine,self).write(values)
        #test code_machine doit etre unique
        if self.env['production.machine'].search_count([('code_machine', '=', self.code_machine)]) > 1:
            raise Warning(_('Erreur!'), 
                        _('Code machine existe déjà [ %s ].')% (self.code_machine))
        return obj_id

    @api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

    @api.multi
    def ajouter_piece(self):
        return { 
                'name': _("Piéce"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'maintenance.piece',
                'view_id': False,
                'context': {'default_machine_id': self.id,},
                }

    @api.multi
    def ajouter_maintenance_preventive(self):
        return { 
                'name': _("Maintenance preventive"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'maintenance.preventive',
                'view_id': False,
                'context': {'default_machine_id': self.id},
                }

    @api.multi
    def ajouter_demande_intervention(self):
        return { 
                'name': _("Demande intervention"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'maintenance.demande.intervention',
                'view_id': False,
                'context': {'default_machine_id': self.id},
                }
    
    @api.multi
    def creer_of(self):
        print self.id
        return { 
                'name': _("OF"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'production.ordre.fabrication',
                'view_id': False,
                'context': {
                'default_activite_id':self.activite_id.id,
                'default_famille_id':self.famille_sortie1.id,
                'default_code_machine':self.id,

                
                },
                }
#----------------------------------------------------------
# color_status
#----------------------------------------------------------
class color_status(models.Model):
    _name = 'color.status'
    state = fields.Selection([('planifie', 'Planifié'),
                              ('demarre', 'Demarré'),
                              ('termine', 'Terminé'),

                              ('brouillon', 'Brouillon'),
                              ('annulee', 'Annulee'),
                              ('attente', 'En attente de réception'),
                              ('recu_partiel', 'Reçu partiellemet'),
                              ('recu_total', 'Reçu totalemet'),
                                ], 'Etat')
    objet = fields.Selection([('ordre_fabrication', 'Ordre fabrication'), 
                              ('commande_client', 'Commande client'),
                              ('commande_fournisseur', 'Commande fournisseur')], 'Objet')
    color = fields.Integer('Coulor')


class production_article_mail(models.Model):
    _name = "production.article"
    _inherit = ['production.article','mail.thread']


class production_zone_stockage(models.Model):
    _name = "production.zone.stockage"

    of_ids = fields.One2many('production.ordre.fabrication', 'zone_stockage_id', 'OF')
    name = fields.Char('Zone de stockage', required=True)

#----------------------------------------------------------
# production_ordre_fabrication
#----------------------------------------------------------
class production_ordre_fabrication(models.Model):

    @api.multi
    @api.depends('article_sortant', 'code_of', 'code_operateur', 'code_machine', 'quantite')
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.code_of + u' { opérateur:' + record.code_operateur.code_operateur + ', machine:' + record.code_machine.code_machine + ', production: ' + str(record.quantite) + ' de ' + record.article_sortant.code_article + ' }')) 
        return result


    #button workflow Démarrer
    @api.one
    def action_demarrer_fabrication(self):
        print '**************************'
        print self.commande_id.id
        wt = self.env['production.commande']
        wt2 = wt.browse(self.commande_id.id)
        wt2.write({'state': 'demarre'})
        self.write({'state': 'demarre'})
        for of in self:
            if of.demarre == False:
                print of.demarre
                of.demarre = True
                print of.demarre
                of.article_entree1.stock_reserve += of.quantite1
                if of.article_sortant.famille_id.article_entree2 == True:
                    of.article_entree2.stock_reserve += of.quantite2


#       for of in self:
#           #on ne peut demarrer un of que si les quantites entrantes soient réservé
#           if of.quantite1 > of.quantite_reserve_entree1:
#               raise Warning(_('Erreur!'), 
#                           _('La quantité entrée1 n\'est pas encore réservé'))
#           if of.article_sortant.famille_id.article_entree2 == True:
#               if of.quantite2 > of.quantite_reserve_entree2:
#                   raise Warning(_('Erreur!'), 
#                               _('La quantité entrée2 n\'est pas encore réservé'))
    

    #button workflow Arréter
    @api.one
    def action_arreter_fabrication(self):
        self.write({'state': 'planifie'})

    #button workflow Terminer
    @api.one
    def action_terminer_fabrication(self):
        self.write({'state': 'termine'})
        wt = self.env['production.commande']
        wt2 = wt.browse(self.commande_id.id)
        wt2.write({'state': 'termine'})

#   @api.onchange('activite_id')
#   def onchange_activite(self):
#       res = {}
#       ids = []
#       if self.env.context.get('default_article_sortant', False) == False:
#           #filter sur les articles sortants selon l'activité selectionnée
#           self.article_sortant = []
#           if self.activite_id:
#               for famille in self.activite_id.activite_famille_sortant_ids:
#                   for article in famille.article_ids:
#                       ids.append(article.id)
#           else:
#               self.env.cr.execute('SELECT id FROM production_article')
#               article_objs = self.env.cr.fetchall()
#               for op in article_objs:
#                   ids.append(op)
#           res['domain'] = {'article_sortant': [('id', 'in', ids)]}
#       return res
    @api.multi
    @api.onchange('activite_id')
    def onchange_activite(self):
        famille_sortant_ids=[]
        res = {}
        activite_ids = self.env['production.activite'].search([('id', '=', self.activite_id.id)])
        for activite in activite_ids:
            famille_sortant_ids=activite.activite_famille_sortant_ids.ids
            print activite.activite_famille_sortant_ids.ids
        #print famille_sortant_ids 
        res['domain'] = {'famille_id': [('id', 'in', famille_sortant_ids)]} 
        return res  
    @api.onchange('famille_id')
    def onchange_famille(self):
        res = {}
        ids = []
        if self.env.context.get('default_article_sortant', False) == False:
            #filter sur les articles sortants selon la famille selectionnée
            self.article_sortant = []
            if self.famille_id:
                for article in self.famille_id.article_ids:
                    ids.append(article.id)
            else:
                self.env.cr.execute('SELECT id FROM production_article')
                article_objs = self.env.cr.fetchall()
                for op in article_objs:
                    ids.append(op)
            res['domain'] = {'article_sortant': [('id', 'in', ids)]}
        return res

    @api.one
    def _get_quantite_realiser(self):
        for of in self:
            bef_ids = self.env['production.bon.entree.fabrication'].search([('code_of', '=', of.id)])
            qte = 0
            for bef in bef_ids:
                qte = qte + bef.quantite
            self.quantite_realiser = qte

    @api.one
    @api.depends('quantite', 'quantite_realiser')
    def _get_progress(self):
        if self.quantite > 0 and self.quantite_realiser > 0:
            self.progress = self.quantite_realiser / self.quantite * 100
        else:
            self.progress = 0

    #method pour filter "OF Prêt à fabriquer"
    @api.one
    @api.depends('quantite1', 'quantite_stock_article_entree1', 'quantite2', 'quantite_stock_article_entree2')
    def _article_entree_exist(self):
        for of in self:
            if of.article_sortant.famille_id.article_entree2 == True:
                if of.quantite1 <= of.quantite_stock_article_entree1 and of.quantite2 <= of.quantite_stock_article_entree2:
                    self.article_entree_exist = True
                else:
                    self.article_entree_exist = False
            else:
                if of.quantite1 <= of.quantite_stock_article_entree1:
                    self.article_entree_exist = True
                else:
                    self.article_entree_exist = False

    @api.one
    @api.depends('state')
    def _check_color(self):
        for rec in self:
            color = 0
            color_value = self.env['color.status'].search([('state', '=', rec.state)], limit=1).color
            if color_value:
                color = color_value

            self.member_color = color

    @api.one
    def _get_bon_entree_count(self):
        for of in self:
            self.bon_entree_count  = self.env['production.bon.entree.fabrication'].search_count([('code_of', '=', of.id)])

    @api.one
    @api.depends('article_entree1')
    def _get_quantite_reserve_entree1(self):
        qte = 0
        if self.article_entree1:
            bon_reservation_ids = self.env['bon.reservation.ordre.fabrication'].search([
                                                                                ('ordre_fabrication_id','=',self.id), 
                                                                                ('article_id', '=', self.article_entree1.id)])
            for br in bon_reservation_ids:
                qte += br.quantite

        self.quantite_reserve_entree1 = qte

    @api.one
    @api.depends('article_entree2')
    def _get_quantite_reserve_entree2(self):
        qte = 0
        if self.article_entree2:
            bon_reservation_ids = self.env['bon.reservation.ordre.fabrication'].search([('ordre_fabrication_id','=',self.id), 
                                                                                ('article_id', '=', self.article_entree2.id)])
            for br in bon_reservation_ids:
                qte += br.quantite

        self.quantite_reserve_entree2 = qte
    @api.one
    def _get_conversion(self):
        self.conversion=""
    @api.model
    def _get_date(self):
        return datetime.now().strftime('%Y-%m-%d')



    _name = 'production.ordre.fabrication'
    
    bon_entree_fabrication_ids = fields.One2many('production.bon.entree.fabrication', 'code_of', 'Bons entrées fabrication')
    bon_reservation_of_ids = fields.One2many('bon.reservation.ordre.fabrication', 'ordre_fabrication_id', 'Bons de réservation')
    bon_entree_count = fields.Integer(compute='_get_bon_entree_count', string='Bons entrées')
    member_color = fields.Integer(compute='_check_color', string='Color')
    activite_id = fields.Many2one('production.activite', 'Activité', ondelete='cascade')
    famille_id = fields.Many2one('production.famille', 'Famille', ondelete='cascade')
    code_of = fields.Char('Code OF :', readonly=True)
    commande_id = fields.Many2one('production.commande', 'Num commande', ondelete='cascade', domain=[('state', '!=', 'termine')])
    line_commande_id = fields.Many2one('article.commande.rel', 'Article commandé', ondelete='cascade')
    article_sortant = fields.Many2one('production.article', 'Article sortant', ondelete='cascade', required=True)
    quantite = fields.Float('Quantité', required=True)
    
    unite_quantite_sortant = fields.Selection([('u','U'),
                                              ('kg','Kg'),
                                              ('m2','m²'),
                                              ('m','m')],string='Unité par Default')
    code_machine = fields.Many2one('production.machine', 'Code Machine', ondelete='cascade', required=True)
    code_operateur = fields.Many2one('production.operateur', 'Code Opérateur', ondelete='cascade', required=True)

    article_entree1 = fields.Many2one('production.article', 'Article entrée1', ondelete='cascade', required=True)
    quantite1 = fields.Float('Quantité1', required=True)
    grade_entree1 = fields.Char('Grade entrée1', default='Selon Référentiel')

    article_entree2 = fields.Many2one('production.article', 'Article entrée2', ondelete='cascade')
    quantite2 = fields.Float('Quantité2')
    grade_entree2 = fields.Char('Grade entrée2', default='Selon Référentiel')

    #champ somme la quantite realise
    quantite_realiser = fields.Integer(compute='_get_quantite_realiser', string='Quantité réalisée', default=0)
    progress = fields.Float(compute='_get_progress', string='Progression', readonly=True, digits=(16,2))

    nbre_par_paquet = fields.Integer('Nombre par paquet')
    grade_sortie = fields.Char('Grade sortie', default='Selon Référentiel')
    tolerance_qte_plus = fields.Char('Tolérance qte plus')
    tolerance_qte_moins = fields.Char('Tolérance qte moins')
    tolerance_dimension = fields.Char('Tolérance dimension')
    cerclage = fields.Boolean('Cerclage')
    zone_stockage_id = fields.Many2one('production.zone.stockage', 'Zone stockage', ondelete='cascade')
    date_debut = fields.Date('Date début', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
    
    #calculer la date fin automatiquement
    date_fin = fields.Date('Date fin', default=lambda self: self._get_date() ,required=True)
    cadence = fields.Float('Cadence')
    remarque = fields.Text('Remarque')
    state = fields.Selection([('planifie','Planifié'),
                              ('demarre','Demarré'),
                              ('termine','Terminé')], 'Etat', readonly=True, default='planifie')
    unite_article_sortant = fields.Selection([('u','U'),
                                              ('kg','Kg'),
                                              ('m2','m²'),
                                              ('m','m')], related='article_sortant.unite')
    quantite_stock_article_sortant = fields.Float('Stk_dispo', related='article_sortant.stock_disponible')
    unite_article_entree1 = fields.Selection([('u','U'),
                                              ('kg','Kg'),
                                              ('m2','m²'),
                                              ('m','m')], related='article_entree1.unite')
    quantite_stock_article_entree1 = fields.Float('En Stock', related='article_entree1.stock_disponible')

    unite_article_entree2 = fields.Selection([('u','U'),
                                              ('kg','Kg'),
                                              ('m2','m²'),
                                              ('m','m')], related='article_entree2.unite')
    quantite_stock_article_entree2 = fields.Float('En Stock', related='article_entree2.stock_disponible')

    article_entree_exist = fields.Boolean(compute='_article_entree_exist', string='Entree exist', store=True)

    article_famille_article_entree2 = fields.Boolean(string='Article entrée2 ?',                                                    related='article_sortant.famille_id.article_entree2')
    article_famille_tolerance_qte_plus = fields.Boolean(string='tolerance_qte_plus ?',
                                                related='article_sortant.famille_id.tolerance_qte_plus')
    article_famille_tolerance_qte_moins = fields.Boolean(string='tolerance_qte_moins ?',
                                                related='article_sortant.famille_id.tolerance_qte_moins')
    article_famille_tolerance_dimension = fields.Boolean(string='tolerance_dimension ?',
                                                related='article_sortant.famille_id.tolerance_dimension')

    quantite_reserve_entree1 = fields.Float(compute='_get_quantite_reserve_entree1', string='Réservé')
    quantite_reserve_entree2 = fields.Float(compute='_get_quantite_reserve_entree2', string='Réservé')
    #champ defini l'etat du of demarré ou pas
    demarre = fields.Boolean(default=False)
    
    #unite de convertion 
    unite_article_a_convertir = fields.Selection([('u','U'), ('kg','Kg'),('m2','m²'), ('m','m')],'Unité De Saisie ' )
    qte_unite_article_a_convertir = fields.Float('Quantité')
    conversion = fields.Char(compute='_get_conversion',string='      ')
     
    @api.onchange('quantite')
    def onchange_texte(self):
        localdict = {
                    'un':self.article_sortant.unite,
                    'qs' : self.quantite,
                    'pu' : self.article_sortant.poids_unit,
                    'mc' : self.article_sortant.dimension_m2,
                    'pl' : self.article_sortant.poids_lineaire,
                    'd' : self.article_sortant.diametre,
                    'dl' : self.article_sortant.diametre_longitudinal,
                    'mt' : self.article_sortant.maille_transversal,
                    'ml' : self.article_sortant.maille_longitudinal,
                    'la' : self.article_sortant.largeur,
                    'lo' : self.article_sortant.longueur,
                    'nl' : self.article_sortant.nbr_Barres_longitudinales,
                    'nt' : self.article_sortant.nbr_Barres_transversales,

                    'q1' : self.quantite1,
                    'pu1' : self.article_entree1.poids_unit,
                    'mc1' : self.article_entree1.dimension_m2,
                    'pl1' : self.article_entree1.poids_lineaire,
                    'd1' : self.article_entree1.diametre,
                    'dl1' : self.article_entree1.diametre_longitudinal,
                    'mt1' : self.article_entree1.maille_transversal,
                    'ml1' : self.article_entree1.maille_longitudinal,
                    'la1' : self.article_entree1.largeur,
                    'lo1' : self.article_entree1.longueur,
                    'nl1' : self.article_entree1.nbr_Barres_longitudinales,
                    'nt1' : self.article_entree1.nbr_Barres_transversales,

                    'q2' : self.quantite2,
                    'pu2' : self.article_entree2.poids_unit,
                    'mc2' : self.article_entree2.dimension_m2,
                    'pl2' : self.article_entree2.poids_lineaire,
                    'd2' : self.article_entree2.diametre,
                    'dl2' : self.article_entree2.diametre_longitudinal,
                    'mt2' : self.article_entree2.maille_transversal,
                    'ml2' : self.article_entree2.maille_longitudinal,
                    'la2' : self.article_entree2.largeur,
                    'lo2' : self.article_entree2.longueur,
                    'nl2' : self.article_entree2.nbr_Barres_longitudinales,
                    'nt2' : self.article_entree2.nbr_Barres_transversales,
                    }
        if self.unite_article_a_convertir!=localdict['un']:
             #faire conversion
             if self.unite_article_a_convertir!=False:
                qte=self.convert(self.unite_article_a_convertir,localdict['un'],localdict['qs'],localdict['pu'],localdict['mc'],localdict['pl'])
                self.qte_unite_article_a_convertir=qte
                strr= str(self.quantite)+'  '+self.unite_article_a_convertir+' ---->  '+ str(self.qte_unite_article_a_convertir)+'  '+localdict['un']
                #change la valeur de champs conversion
                self.conversion=strr
            
            
        else:
             self.conversion=''
             if self.unite_article_a_convertir!=False:
                self.qte_unite_article_a_convertir=self.quantite
            
            



    @api.onchange('unite_article_a_convertir')
    def onchange_convertion(self):
        
        localdict = {
                    'un':self.article_sortant.unite,
                    'qs' : self.quantite,
                    'pu' : self.article_sortant.poids_unit,
                    'mc' : self.article_sortant.dimension_m2,
                    'pl' : self.article_sortant.poids_lineaire,
                    'd' : self.article_sortant.diametre,
                    'dl' : self.article_sortant.diametre_longitudinal,
                    'mt' : self.article_sortant.maille_transversal,
                    'ml' : self.article_sortant.maille_longitudinal,
                    'la' : self.article_sortant.largeur,
                    'lo' : self.article_sortant.longueur,
                    'nl' : self.article_sortant.nbr_Barres_longitudinales,
                    'nt' : self.article_sortant.nbr_Barres_transversales,

                    'q1' : self.quantite1,
                    'pu1' : self.article_entree1.poids_unit,
                    'mc1' : self.article_entree1.dimension_m2,
                    'pl1' : self.article_entree1.poids_lineaire,
                    'd1' : self.article_entree1.diametre,
                    'dl1' : self.article_entree1.diametre_longitudinal,
                    'mt1' : self.article_entree1.maille_transversal,
                    'ml1' : self.article_entree1.maille_longitudinal,
                    'la1' : self.article_entree1.largeur,
                    'lo1' : self.article_entree1.longueur,
                    'nl1' : self.article_entree1.nbr_Barres_longitudinales,
                    'nt1' : self.article_entree1.nbr_Barres_transversales,

                    'q2' : self.quantite2,
                    'pu2' : self.article_entree2.poids_unit,
                    'mc2' : self.article_entree2.dimension_m2,
                    'pl2' : self.article_entree2.poids_lineaire,
                    'd2' : self.article_entree2.diametre,
                    'dl2' : self.article_entree2.diametre_longitudinal,
                    'mt2' : self.article_entree2.maille_transversal,
                    'ml2' : self.article_entree2.maille_longitudinal,
                    'la2' : self.article_entree2.largeur,
                    'lo2' : self.article_entree2.longueur,
                    'nl2' : self.article_entree2.nbr_Barres_longitudinales,
                    'nt2' : self.article_entree2.nbr_Barres_transversales,
                    }
        if self.unite_article_a_convertir!=localdict['un']:
             #faire conversion
             if self.unite_article_a_convertir!=False:
                qte=self.convert(self.unite_article_a_convertir,localdict['un'],localdict['qs'],localdict['pu'],localdict['mc'],localdict['pl'])
                self.qte_unite_article_a_convertir=qte
                strr= str(self.quantite)+'  '+self.unite_article_a_convertir+' ---->  '+ str(self.qte_unite_article_a_convertir)+'  '+localdict['un']
                #change la valeur de champs conversion
                self.conversion=strr
            
            
        else:
             self.conversion=''
             if self.unite_article_a_convertir!=False:
                self.qte_unite_article_a_convertir=self.quantite

        

    @api.model
    def create(self, values):
      

      
        
        
        #self.env['production.commande'].browse(values['commande_id']).write({'state': 'planifie'})
        wt = self.env['production.commande']

        wt2 = wt.browse(values['commande_id'])

        wt2.write({'state': 'planifie'})
        if values['quantite'] <= 0:
            raise Warning(_('Erreur!'), 
                        _('La quantité sortant doit étre supérieur strictement à zero ( %s )')% (values['quantite']))

        #test si quantite article_entrant1 <= 0 on genere exception
        if values['quantite1'] <= 0:
            raise Warning(_('Erreur!'), 
                        _('La quantité entrant1 doit étre supérieur strictement à zero ( %s )')% (values['quantite1']))

        #test si quantite article_entrant2 <= 0 on genere exception
        if values['article_famille_article_entree2'] == True:
            if values['quantite2'] <= 0:
                raise Warning(_('Erreur!'), 
                            _('La quantité entrant2 doit étre supérieur strictement à zero ( %s )')% (values['quantite2']))

        #test date debut < date fin
        if values['date_fin'] < values['date_debut']:
            raise Warning(_('Erreur!'), 
                        _('Date début doit être inférieur ou égal à la Date fin'))
        #generer code sequence "code_of"
        values['code_of'] = self.env['ir.sequence'].get('production.ordre.fabrication')
        #self.env['article.machine.rel'].create({code_bon:'AAAA',date_bon:,client_id,commande_id:,article_id:3,quantite:4})
        id_of=super(production_ordre_fabrication, self).create(values)
        
        self.env['bon.reservation.ordre.fabrication'].create({'code_bon':'OF','date_bon':datetime.now().strftime('%Y-%m-%d'),'ordre_fabrication_id':id_of.id,'article_id':values['article_entree1'],'quantite':values['quantite1'],'quantite_demande':values['quantite1']})
        if values['article_entree2']:
           self.env['bon.reservation.ordre.fabrication'].create({'code_bon':'OF','date_bon':datetime.now().strftime('%Y-%m-%d'),'ordre_fabrication_id':id_of.id,'article_id':values['article_entree2'],'quantite':values['quantite2'],'quantite_demande':values['quantite2']})
        return id_of

    @api.multi
    def write(self, values):
        obj_id=super(production_ordre_fabrication, self).write(values)
        for obj in self:
            #test si quantite article_sortant <= 0 on genere exception
            if obj.quantite <= 0:
                raise Warning(_('Erreur!'), 
                            _('La quantité sortant doit étre supérieur strictement à zero ( %s )')% (obj.quantite))
            #test si quantite article_entrant1 <= 0 on genere exception
            if obj.quantite1 <= 0:
                raise Warning(_('Erreur!'), 
                            _('La quantité entrant1 doit étre supérieur strictement à zero ( %s )')% (obj.quantite1))
            #test si quantite article_entrant2 <= 0 on genere exception
            if obj.article_sortant.famille_id.article_entree2 == True:
                if obj.quantite2 <= 0:
                    raise Warning(_('Erreur!'), 
                                _('La quantité entrant2 doit étre supérieur strictement à zero ( %s )')% (obj.quantite2))
            #test date debut < date fin
            if obj.date_fin < obj.date_debut:
                raise Warning(_('Erreur!'), 
                            _('Date début doit être inférieur ou égal à la Date fin'))

        return obj_id


    @api.onchange('article_sortant','quantite','article_entree1','article_entree2')
    def onchange_formule(self):
        self.quantite1 = 0
        self.quantite2 = 0
        localdict = {
                    'qs' : self.quantite,
                    'pu' : self.article_sortant.poids_unit,
                    'mc' : self.article_sortant.dimension_m2,
                    'pl' : self.article_sortant.poids_lineaire,
                    'd' : self.article_sortant.diametre,
                    'dl' : self.article_sortant.diametre_longitudinal,
                    'mt' : self.article_sortant.maille_transversal,
                    'ml' : self.article_sortant.maille_longitudinal,
                    'la' : self.article_sortant.largeur,
                    'lo' : self.article_sortant.longueur,
                    'nl' : self.article_sortant.nbr_Barres_longitudinales,
                    'nt' : self.article_sortant.nbr_Barres_transversales,

                    'q1' : self.quantite1,
                    'pu1' : self.article_entree1.poids_unit,
                    'mc1' : self.article_entree1.dimension_m2,
                    'pl1' : self.article_entree1.poids_lineaire,
                    'd1' : self.article_entree1.diametre,
                    'dl1' : self.article_entree1.diametre_longitudinal,
                    'mt1' : self.article_entree1.maille_transversal,
                    'ml1' : self.article_entree1.maille_longitudinal,
                    'la1' : self.article_entree1.largeur,
                    'lo1' : self.article_entree1.longueur,
                    'nl1' : self.article_entree1.nbr_Barres_longitudinales,
                    'nt1' : self.article_entree1.nbr_Barres_transversales,

                    'q2' : self.quantite2,
                    'pu2' : self.article_entree2.poids_unit,
                    'mc2' : self.article_entree2.dimension_m2,
                    'pl2' : self.article_entree2.poids_lineaire,
                    'd2' : self.article_entree2.diametre,
                    'dl2' : self.article_entree2.diametre_longitudinal,
                    'mt2' : self.article_entree2.maille_transversal,
                    'ml2' : self.article_entree2.maille_longitudinal,
                    'la2' : self.article_entree2.largeur,
                    'lo2' : self.article_entree2.longueur,
                    'nl2' : self.article_entree2.nbr_Barres_longitudinales,
                    'nt2' : self.article_entree2.nbr_Barres_transversales,
                    }
        if self.article_sortant.famille_id.article_entree2 == True:
            #Calcul q1 et q2 (2 articles entrant)
            if self.article_sortant and self.article_entree1 and self.article_entree2 and self.quantite > 0:
                for param in self.article_sortant.famille_id.famille_entrant_param2_ids:
                    if param.famille_entrant1_id.id == self.article_entree1.famille_id.id and param.famille_entrant2_id.id == self.article_entree2.famille_id.id:
                        # 1 # si unite <> unite_qs ==> convert
                        if self.article_sortant.unite <> param.unite_qs:
                            localdict['qs'] = self.convert(self.article_sortant.unite, param.unite_qs, self.quantite, localdict.get("pu", None), localdict.get("mc", None), localdict.get("pl", None))
                        # 2 # execution du formule q1
                        try:
                            localdict['q1'] = eval(param.calcul_quantite1, localdict)
                        except:
                            pass
                        # 3 # execution du formule q2
                        try:
                            localdict['q2'] = eval(param.calcul_quantite2, localdict)
                        except:
                            pass

                        # 4 # si unite <> unite_q1 ==> convert
                        if self.article_entree1.unite <> param.unite_q1:
                            localdict['q1'] = self.convert(param.unite_q1, self.article_entree1.unite, localdict.get("q1", None), localdict.get("pu1", None), localdict.get("mc1", None), localdict.get("pl1", None))
                        # 5 # si unite <> unite_q2 ==> convert
                        if self.article_entree2.unite <> param.unite_q2:
                            localdict['q2'] = self.convert(param.unite_q2, self.article_entree2.unite, localdict.get("q2", None), localdict.get("pu2", None), localdict.get("mc2", None), localdict.get("pl2", None))

                        break
        else:
            #Calcul q1 (un seul article entrant)
            if self.article_sortant and self.article_entree1 and self.quantite > 0:
                for param in self.article_sortant.famille_id.famille_entrant_param_ids:
                    if param.famille_entrant1_id.id == self.article_entree1.famille_id.id:
                        # 1 # si us1 <> us2 ==> convert
                        if self.article_sortant.unite <> param.unite_qs:
                            localdict['qs'] = self.convert(self.article_sortant.unite, param.unite_qs, self.quantite, localdict.get("pu", None), localdict.get("mc", None), localdict.get("pl", None))
                        # 2 # execution du formule q1
                        try:
                            localdict['q1'] = eval(param.calcul_quantite1, localdict)
                        except:
                            pass

                        # 3 # si ue1 <> ue2 ==> convert
                        if self.article_entree1.unite <> param.unite_q1:
                            localdict['q1'] = self.convert(param.unite_q1, self.article_entree1.unite, localdict.get("q1", None), localdict.get("pu1", None), localdict.get("mc1", None), localdict.get("pl1", None))

                        break
        self.quantite1 = localdict.get("q1", None)  
        self.quantite2 = localdict.get("q2", None)

    #method qui convert qte en (u1) vers (u2)
    def convert(self, u1, u2, qte, pu, mc, pl):
        if u1 == "m":
            if u2 == "kg":
                qte = qte * pl
            else:
                if u2 == "u":
                    qte = qte * pl / pu
                else:
                    if u2 == "m2":
                        qte = qte * pl / pu * mc
        else:
            if u1 == "kg":
                if u2 == "m":
                    qte = qte / pl
                else:
                    if u2 == "u":
                        qte = qte / pu
                    else:
                        if u2 == "m2":
                            qte = qte / pu * mc
            else:
                if u1 == "u":
                    if u2 == "m":
                        qte = qte * pu / pl
                    else:
                        if u2 == "kg":
                            qte = qte * pu
                        else:
                            if u2 == "m2":
                                qte = qte * mc
                else:
                    if u1 == "m2":
                        if u2 == "m":
                            qte = qte / mc * pu / pl
                        else:
                            if u2 == "kg":
                                qte = qte / mc * pu
                            else:
                                if u2 == "u":
                                    qte = qte / mc
        return qte

    def valider_condition(self, article_ids, conditions, article_sortant, e):
        res_article_ids = []
        localdict = {
                    'pu' : article_sortant.poids_unit,
                    'mc' : article_sortant.dimension_m2,
                    'pl' : article_sortant.poids_lineaire,
                    'd' : article_sortant.diametre,
                    'dl' : article_sortant.diametre_longitudinal,
                    'mt': article_sortant.maille_transversal,
                    'ml': article_sortant.maille_longitudinal,
                    'la' : article_sortant.largeur,
                    'lo' : article_sortant.longueur,
                    'nl' : article_sortant.nbr_Barres_longitudinales,
                    'nt' : article_sortant.nbr_Barres_transversales,
                    }
        for a in article_ids:
            if e == "e1":
                localdict['pu1'] = a.poids_unit
                localdict['mc1'] = a.dimension_m2
                localdict['pl1'] = a.poids_lineaire
                localdict['d1'] = a.diametre
                localdict['dl1'] = a.diametre_longitudinal
                localdict['mt1'] = a.maille_transversal
                localdict['ml1'] = a.maille_longitudinal
                localdict['la1'] = a.largeur
                localdict['lo1'] = a.longueur
                localdict['nl1'] = a.nbr_Barres_longitudinales
                localdict['nt1'] = a.nbr_Barres_transversales
            else:
                if e == "e2":
                    localdict['pu2'] = a.poids_unit
                    localdict['mc2'] = a.dimension_m2
                    localdict['pl2'] = a.poids_lineaire
                    localdict['d2'] = a.diametre
                    localdict['dl2'] = a.diametre_longitudinal
                    localdict['mt2'] = a.maille_transversal
                    localdict['ml2'] = a.maille_longitudinal
                    localdict['la2'] = a.largeur
                    localdict['lo2'] = a.longueur
                    localdict['nl2'] = a.nbr_Barres_longitudinales
                    localdict['nt2'] = a.nbr_Barres_transversales
            valide = True
            for c in conditions:
                try:
                    if eval(c.condition, localdict) != True:
                        valide = False
                        break
                except:
                    pass
            if valide == True:
                res_article_ids.append(a.id)

        return res_article_ids

    @api.onchange('article_sortant')
    def onchange_article_sortant(self):
        self.code_machine = []
        self.article_entree1 = []
        self.article_entree2 = []
        res = {}
        dictionaire = {}
        if self.article_sortant:
            #filter sur les machines selon article_sortant
            machine_ids = []
            for ligne in self.article_sortant.article_machine_ids:
                machine_ids.append(ligne.machine_id.id)
            dictionaire['code_machine'] = [('id', 'in', machine_ids)]

            #filter sur les articles entrants
            #si 2 article entrant
            if self.article_sortant.famille_id.article_entree2 == True:
                res_article_e1_ids = []
                res_article_e2_ids = []
                for param in self.article_sortant.famille_id.famille_entrant_param2_ids:
                    article_ids = self.env['production.article'].search([('famille_id', '=', param.famille_entrant1_id.id)])
                    for a_id in self.valider_condition(article_ids, param.production_condition_ids, self.article_sortant, "e1"):
                        res_article_e1_ids.append(a_id)

                    article2_ids = self.env['production.article'].search([('famille_id', '=', param.famille_entrant2_id.id)])
                    for a_id in self.valider_condition(article2_ids, param.production_condition_ids, self.article_sortant, "e2"):
                        res_article_e2_ids.append(a_id)

                dictionaire['article_entree1'] = [('id', 'in', res_article_e1_ids)]
                dictionaire['article_entree2'] = [('id', 'in', res_article_e2_ids)]


            #un seul article entrant
            else:
                res_article_e1_ids = []
                for param in self.article_sortant.famille_id.famille_entrant_param_ids:
                    article_ids = self.env['production.article'].search([('famille_id', '=', param.famille_entrant1_id.id)])
                    for a_id in self.valider_condition(article_ids, param.production_condition_ids, self.article_sortant, "e1"):
                        res_article_e1_ids.append(a_id)

                dictionaire['article_entree1'] = [('id', 'in', res_article_e1_ids)]

        else:
            #all code_machine
            self.env.cr.execute('SELECT id FROM production_machine')
            machine_objs = self.env.cr.fetchall()
            machine_ids = []
            for m in machine_objs:
                machine_ids.append(m[0])
            dictionaire['code_machine'] = [('id', 'in', machine_ids)]

            #all article
            self.env.cr.execute('SELECT id FROM production_article')
            article_objs = self.env.cr.fetchall()
            article_ids = []
            for a in article_objs:
                article_ids.append(a[0])
            dictionaire['article_entree1'] = [('id', 'in', article_ids)]
            dictionaire['article_entree2'] = [('id', 'in', article_ids)]

        res['domain'] = dictionaire
        return res

    @api.onchange('code_machine')
    def onchange_code_machine(self):
        #on cherche la cadence a partir du relation article.machine.rel
        self.cadence = 0
        if self.article_sortant and self.code_machine:
            cadence_val = self.env['article.machine.rel'].search([('article_id', '=', self.article_sortant.id),
                                                                  ('machine_id', '=', self.code_machine.id)], 
                                                                  limit=1).cadence
            if cadence_val:
                self.cadence = cadence_val

        #filter sur les operateurs qualifier pour la machine selectionnée
        self.code_operateur = []
        res = {}
        ids = []
        if self.code_machine:
            op_ma_ids = self.env['operateur.machine.rel'].search([('machine_id', '=', self.code_machine.id)])
            for op_ma in op_ma_ids:
                ids.append(op_ma.operateur_id.id)
        else:
            self.env.cr.execute('SELECT id FROM production_operateur')
            operateur_objs = self.env.cr.fetchall()
            for op in operateur_objs:
                ids.append(op)
        res['domain'] = {'code_operateur': [('id', 'in', ids)]}
        return res

    @api.onchange('article_entree1')
    def onchange_article_entree1(self):
        res = {}
        res_article_e2_ids = []
        #si 2 articles entrants
        if self.article_sortant.famille_id.article_entree2 == True:
            #filter pour le champ article_entree2
            self.article_entree2 = []
            #article2 = self.article_entree2.id
            if self.article_sortant and self.article_entree1:
                for param in self.article_sortant.famille_id.famille_entrant_param2_ids:
                    if self.article_entree1.famille_id.id == param.famille_entrant1_id.id:
                        article2_ids = self.env['production.article'].search([('famille_id', '=', param.famille_entrant2_id.id)])
                        for a_id in self.valider_condition(article2_ids, param.production_condition_ids, self.article_sortant, "e2"):
                            res_article_e2_ids.append(a_id)

        res['domain'] = {'article_entree2': [('id', 'in', res_article_e2_ids)]}
        
        return res

#   @api.onchange('commande_id')
#   def onchange_commande_id(self):
#       res = {}
#       ids = []
#       if self.commande_id:
#           for article in self.commande_id.article_commande_ids:
#               ids.append(article.id)
#       else:
#           self.env.cr.execute('SELECT id FROM production_article')
#           article_objs = self.env.cr.fetchall()
#           for a in article_objs:
#               ids.append(a)

#       res['domain'] = {'article_sortant': [('id', 'in', ids)]}        
#       return res

    @api.multi
    def ajouter_bon_entree_fabrication(self):
        bon_form = self.env.ref('production.production_bon_entree_fabrication_form_popup', False)
        return { 
                'name': _("Bon entrée fabrication"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'production.bon.entree.fabrication',
                'views': [(bon_form.id, 'form')],
                'view_id': 'bon_form.id',
                'target': 'new',
                'context': {'default_code_of': self.id},
                }

    @api.multi
    def reserver_pour_entree1(self):
        return { 
                'name': _("Bon de réservation"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'bon.reservation.ordre.fabrication',
                'view_id': False,
                'context': { 
                            'default_ordre_fabrication_id': self.id,
                            'default_article_id': self.article_entree1.id,
                            'default_quantite': self.quantite1,
                            'default_quantite_demande': self.quantite1,
                            },
                }

    @api.multi
    def creer_of_from_entree1(self):
        nbr_days = abs(datetime.strptime(self.date_debut, DEFAULT_SERVER_DATE_FORMAT).date() - datetime.strptime(self.date_fin, DEFAULT_SERVER_DATE_FORMAT).date())/2
        date_prevue = str(datetime.strptime(self.date_debut, DEFAULT_SERVER_DATE_FORMAT).date() + nbr_days)
    
        return { 
                'name': _("Ordre fabrication"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'production.ordre.fabrication',
                'view_id': False,
                'context': {
                            'default_commande_id': self.commande_id.id, 
                            'default_article_sortant': self.article_entree1.id,
                            'default_quantite': self.quantite1,
                            'default_date_fin': date_prevue
                            },
                }

#   @api.multi
#   def creer_commande_entree1(self):
#       return { 
#               'name': _("Commande fournisseur"),
#               'type': 'ir.actions.act_window',
#               'view_type': 'form',
#               'view_mode': 'form',
#               'res_model': 'article.commande.fournisseur.rel',
#               'view_id': False,
#               'context': { 
#                           'default_article_id': self.article_entree1.id,
#                           'default_quantite': self.quantite1,
#                           },
#               }

    @api.multi
    def creer_demande_entree1(self):
        return { 
                'name': _("Demande d'achat"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'demande.achat',
                'view_id': False,
                'context': { 
                            'default_article_id': self.article_entree1.id,
                            'default_quantite_demande': self.quantite1,
                            },
                }

    @api.multi
    def reserver_pour_entree2(self):
        return { 
                'name': _("Bon de réservation"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'bon.reservation.ordre.fabrication',
                'view_id': False,
                'context': { 
                            'default_ordre_fabrication_id': self.id,
                            'default_article_id': self.article_entree2.id,
                            'default_quantite': self.quantite2,
                            'default_quantite_demande': self.quantite2,
                            },
                }

    @api.multi
    def creer_of_from_entree2(self):
        nbr_days = abs(datetime.strptime(self.date_debut, DEFAULT_SERVER_DATE_FORMAT).date() - datetime.strptime(self.date_fin, DEFAULT_SERVER_DATE_FORMAT).date())/2
        date_prevue = str(datetime.strptime(self.date_debut, DEFAULT_SERVER_DATE_FORMAT).date() + nbr_days)

        return { 
                'name': _("Ordre fabrication"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'production.ordre.fabrication',
                'view_id': False,
                'context': {
                            'default_commande_id': self.commande_id.id, 
                            'default_article_sortant': self.article_entree2.id,
                            'default_quantite': self.quantite2,
                            'default_date_fin': date_prevue
                            },
                }

#   @api.multi
#   def creer_commande_entree2(self):
#       return { 
#               'name': _("Commande fournisseur"),
#               'type': 'ir.actions.act_window',
#               'view_type': 'form',
#               'view_mode': 'form',
#               'res_model': 'article.commande.fournisseur.rel',
#               'view_id': False,
#               'context': { 
#                           'default_article_id': self.article_entree2.id,
#                           'default_quantite': self.quantite2,
#                           },
#               }

    @api.multi
    def creer_demande_entree2(self):
        return { 
                'name': _("Demande d'achat"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'demande.achat',
                'view_id': False,
                'context': { 
                            'default_article_id': self.article_entree2.id,
                            'default_quantite_demande': self.quantite2,
                            },
                }


#----------------------------------------------------------
# production_bon_entree_fabrication
#----------------------------------------------------------
class production_bon_entree_fabrication(models.Model):

    @api.one
    @api.depends('code_of')
    def _get_quantite_restante(self):
        qte = self.code_of.quantite
        for bef in self.env['production.bon.entree.fabrication'].search([('code_of', '=', self.code_of.id)]):
            qte = qte - bef.quantite
        self.qte_restante = qte

    _name = 'production.bon.entree.fabrication'

    code_bon = fields.Char('Code bon :', readonly=True)
    code_of = fields.Many2one('production.ordre.fabrication', 'Code OF', ondelete='cascade', required=True, 
                                domain=[('state','=','demarre')])
    quantite = fields.Float('Quantité', required=True)
    duree = fields.Float('Durée' , required=True)
    date_bon = fields.Date('Date bon' , required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], related='code_of.unite_article_sortant')
    qte_restante = fields.Integer(compute='_get_quantite_restante', string='Quantité restante')

    @api.model
    def create(self, values):
        #test si quantite <= 0 on genere exception
        if values['quantite'] <= 0:
            raise Warning(_('Erreur!'), 
                        _('La quantité doit étre supérieur strictement à zero ( %s )')% (values['quantite']))

        #test si duree <= 0 on genere exception
        if values['duree'] <= 0:
            raise Warning(_('Erreur!'),
                        _('La duree doit étre supérieur strictement à zero'))

        #generer code sequence "code_bon"
        values['code_bon'] = self.env['ir.sequence'].get('production.bon.entree.fab')

        for of in self.env['production.ordre.fabrication'].browse(values['code_of']):
            #augmenter stock article sortant
            of.article_sortant.stock_reel += values['quantite']

            #test stock maximale
            of.article_sortant.verifier_stock()

            #Calcul du rapport : qte_realisé / qte_total
            qte_realise_pc = values['quantite'] / of.quantite
            #retirer stock article entrée1
            qte_realise1 = of.quantite1 * qte_realise_pc
            of.article_entree1.stock_reserve -= qte_realise1
            of.article_entree1.stock_reel -= qte_realise1

            if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                #retirer stock article entrée2
                qte_realise2 = of.quantite2 * qte_realise_pc
                of.article_entree2.stock_reserve -= qte_realise2
                of.article_entree2.stock_reel -= qte_realise2

        new_id = super(production_bon_entree_fabrication, self).create(values)
        return new_id

    @api.multi
    def write(self, values):
        nouv_quantite = values.get('quantite', None)
        nouv_of = values.get('code_of', None)
        nouv_duree = values.get('duree', None)
        #test si duree <= 0 on genere exception
        if nouv_duree:
            if nouv_duree <= 0:
                raise Warning(_('Erreur!'), 
                            _('La duree doit étre supérieur strictement à zero'))

        #test si quantite <= 0 on genere exception
        if nouv_quantite:
            if nouv_quantite <= 0:
                raise Warning(_('Erreur!'), 
                            _('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))
        if nouv_of:
            if nouv_quantite:
                #modifier stock
                for of in self.env['production.ordre.fabrication'].browse(self.code_of.id):
                    #modifier stock article sortant
                    of.article_sortant.stock_reel -= self.quantite

                    #Calcul du rapport : qte_realisé / qte_total
                    qte_realise_pc = self.quantite / of.quantite
                    #retirer stock article entrée1
                    qte_realise1 = of.quantite1 * qte_realise_pc
                    of.article_entree1.stock_reserve += qte_realise1
                    of.article_entree1.stock_reel += qte_realise1

                    if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                        #retirer stock article entrée2
                        qte_realise2 = of.quantite2 * qte_realise_pc
                        of.article_entree2.stock_reserve += qte_realise2
                        of.article_entree2.stock_reel += qte_realise2

                for of in self.env['production.ordre.fabrication'].browse(nouv_of):
                    #augmenter stock article sortant
                    of.article_sortant.stock_reel += nouv_quantite

                    #test stock maximale
                    of.article_sortant.verifier_stock()

                    #Calcul du rapport : qte_realisé / qte_total
                    qte_realise_pc = nouv_quantite / of.quantite
                    #retirer stock article entrée1
                    qte_realise1 = of.quantite1 * qte_realise_pc
                    of.article_entree1.stock_reserve -= qte_realise1
                    of.article_entree1.stock_reel -= qte_realise1

                    if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                        #retirer stock article entrée2
                        qte_realise2 = of.quantite2 * qte_realise_pc
                        of.article_entree2.stock_reserve -= qte_realise2
                        of.article_entree2.stock_reel -= qte_realise2


            else:#même quantite
                #modifier stock
                for of in self.env['production.ordre.fabrication'].browse(self.code_of.id):
                    #modifier stock article sortant
                    of.article_sortant.stock_reel -= self.quantite

                    #Calcul du rapport : qte_realisé / qte_total
                    qte_realise_pc = self.quantite / of.quantite
                    #retirer stock article entrée1
                    qte_realise1 = of.quantite1 * qte_realise_pc
                    of.article_entree1.stock_reserve += qte_realise1
                    of.article_entree1.stock_reel += qte_realise1

                    if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                        #retirer stock article entrée2
                        qte_realise2 = of.quantite2 * qte_realise_pc
                        of.article_entree2.stock_reserve += qte_realise2
                        of.article_entree2.stock_reel += qte_realise2

                for of in self.env['production.ordre.fabrication'].browse(nouv_of):
                    #augmenter stock article sortant
                    of.article_sortant.stock_reel += self.quantite

                    #test stock maximale
                    of.article_sortant.verifier_stock()

                    #Calcul du rapport : qte_realisé / qte_total
                    qte_realise_pc = self.quantite / of.quantite
                    #retirer stock article entrée1
                    qte_realise1 = of.quantite1 * qte_realise_pc
                    of.article_entree1.stock_reserve -= qte_realise1
                    of.article_entree1.stock_reel -= qte_realise1

                    if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                        #retirer stock article entrée2
                        qte_realise2 = of.quantite2 * qte_realise_pc
                        of.article_entree2.stock_reserve -= qte_realise2
                        of.article_entree2.stock_reel -= qte_realise2


        else:#même code_of
            if nouv_quantite:
                for of in self.env['production.ordre.fabrication'].browse(self.code_of.id):
                    #modifier stock article sortant
                    of.article_sortant.stock_reel += nouv_quantite - self.quantite

                    #test stock maximale
                    of.article_sortant.verifier_stock()

                    #Calcul du rapport : qte_realisé / qte_total
                    ancien_qte_realise_pc = self.quantite / of.quantite
                    nouveau_qte_realise_pc = nouv_quantite / of.quantite

                    #modifier stock article entrée1
                    ancien_qte_realise1 = of.quantite1 * ancien_qte_realise_pc
                    nouveau_qte_realise1 = of.quantite1 * nouveau_qte_realise_pc
                    of.article_entree1.stock_reserve += ancien_qte_realise1 - nouveau_qte_realise1
                    of.article_entree1.stock_reel += ancien_qte_realise1 - nouveau_qte_realise1

                    if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                        #modifier stock article entrée2
                        ancien_qte_realise2 = of.quantite2 * ancien_qte_realise_pc
                        nouveau_qte_realise2 = of.quantite2 * nouveau_qte_realise_pc
                        of.article_entree2.stock_reserve += ancien_qte_realise2 - nouveau_qte_realise2
                        of.article_entree2.stock_reel += ancien_qte_realise2 - nouveau_qte_realise2


        obj_id=super(production_bon_entree_fabrication, self).write(values)

        return obj_id

    @api.multi
    def unlink(self):
        for rec in self:
            for of in self.env['production.ordre.fabrication'].browse(rec.code_of.id):
                #modifier stock article sortant
                of.article_sortant.stock_reel -= rec.quantite

                #Calcul du rapport : qte_realisé / qte_total
                qte_realise_pc = rec.quantite / of.quantite
                #modifier stock article entrée1
                qte_realise1 = of.quantite1 * qte_realise_pc
                of.article_entree1.stock_reserve += qte_realise1
                of.article_entree1.stock_reel += qte_realise1

                if of.article_sortant.famille_id.article_entree2:#si 2 article entrant
                    #modifier stock article entrée2
                    qte_realise2 = of.quantite2 * qte_realise_pc
                    of.article_entree2.stock_reserve += qte_realise2
                    of.article_entree2.stock_reel += qte_realise2

        return super(production_bon_entree_fabrication, self).unlink()


#----------------------------------------------------------
# bon_reservation_ordre_fabrication
#----------------------------------------------------------
class bon_reservation_ordre_fabrication(models.Model):

    @api.one
    @api.depends('quantite_demande', 'quantite_reserve')
    def _get_progress_reserve_demande(self):
        if self.quantite_demande > 0 and self.quantite_reserve > 0:
            self.progress_reserve_demande = self.quantite_reserve / self.quantite_demande * 100
        else:
            self.progress_reserve_demande = 0

    @api.one
    @api.depends('article_id', 'ordre_fabrication_id')
    def _get_quantite_reserve(self):
        qte = 0
        if self.article_id and self.ordre_fabrication_id:
            bon_reservation_ids = self.env['bon.reservation.ordre.fabrication'].search([
                                                        ('ordre_fabrication_id', '=', self.ordre_fabrication_id.id), 
                                                        ('article_id', '=', self.article_id.id)])
            for br in bon_reservation_ids:
                qte += br.quantite

        self.quantite_reserve = qte

    _name = 'bon.reservation.ordre.fabrication'

    code_bon = fields.Char('Code bon :', readonly=True)
    date_bon = fields.Date('Date bon', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'), readonly=True)

    ordre_fabrication_id = fields.Many2one('production.ordre.fabrication', 'Code OF', ondelete='cascade', required=True,
                                    domain=[('id', 'in', [])])
    article_id = fields.Many2one('production.article', 'Code article', ondelete='cascade', required=True,
                                    domain=[('id', 'in', [])])
    quantite = fields.Float('Quantité', required=True)
    remarque = fields.Text('Remarque')
    
    quantite_demande = fields.Float('Quantité demandé', readonly=True)
    quantite_reserve = fields.Float(compute='_get_quantite_reserve', string='Quantité réservé')
    stock_disponible = fields.Float('Stock disponible', related='article_id.stock_disponible')
    stock_non_reserve = fields.Float('Stock non réservé', related='article_id.stock_non_reserve')

    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], related='article_id.unite', readonly=True, string='Unite')
    progress_reserve_demande = fields.Float(compute='_get_progress_reserve_demande', string='Progression quantité réservé')
    
    etat = fields.Selection([('satisfait','Satisfait'),
                              ('nonsatisfait','Non Satisfait')]
                              , 'Etat',  default='satisfait')
    @api.model
    def create(self, values):
        #test si quantite <= 0 on genere exception
        if values['quantite'] <= 0:
            raise Warning(_('Erreur!'), 
                        _('La quantité doit étre supérieur strictement à zero ( %s )')% (values['quantite']))

        #test si quantite à réservé > stock_non_réservé ==> exception
        article_obj = self.env['production.article'].browse(values['article_id'])

        if values['quantite'] > article_obj.stock_non_reserve:
           #self.write({'etat': 'nonsatisfait'})
           #print 'non satisfait'
           values['etat']='nonsatisfait'
            #raise Warning(_('Erreur!'), 
                        #_('La quantité à réservé est supérieur à la quantité stock disponible'))

        #augmenter le stock_reserve
        article_obj.stock_reserve += values['quantite']

        #generer code sequence "code_bon"
        values['code_bon'] = self.env['ir.sequence'].get('bon.reservation.of')

        new_id = super(bon_reservation_ordre_fabrication, self).create(values)

        return new_id

    @api.multi
    def write(self, values):
        article_obj = self.env['production.article'].browse(self.article_id.id)
        nouv_quantite = values.get('quantite', None)
        if nouv_quantite:
            #test si quantite <= 0 on genere exception
            if nouv_quantite <= 0:
                raise Warning(_('Erreur!'), 
                            _('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

            #test si quantite à réservé > stock_non_réservé ==> exception
            if (nouv_quantite - self.quantite) > article_obj.stock_non_reserve:
                raise Warning(_('Erreur!'), 
                            _('La quantité à réservé est supérieur à la quantité stock disponible'))

            #modifier le stock_reserve
            article_obj.stock_reserve += nouv_quantite - self.quantite

        obj_id=super(bon_reservation_ordre_fabrication, self).write(values)

        return obj_id

    @api.multi
    def unlink(self):
        for rec in self:
            article_obj = self.env['production.article'].browse(rec.article_id.id)
            #retirer la qte stock reserve
            article_obj.stock_reserve -= rec.quantite

        return super(bon_reservation_ordre_fabrication, self).unlink()

