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

#----------------------------------------------------------
# taux_tva
#----------------------------------------------------------
class taux_tva(models.Model):

    _name = 'taux.tva'
    _rec_name = 'taux_tva'

    client_ids = fields.One2many('vente.client', 'taux_tva_id', 'Clients')
    taux_tva = fields.Float('Taux TVA', required=True)
    default = fields.Boolean('Défaut')
 
    @api.model
    def create(self, values):
        if values['default'] == True:
            obj_ids = self.search([('default', '=', True)])
            if len(obj_ids) > 0:
                raise Warning(_('Erreur!'), 
                            _('Il faut un seul valeur par défaut'))
        #taux_tva doit etre unique
        taux_tva_count = self.search_count([('taux_tva', '=', values['taux_tva'])])
        if taux_tva_count > 0:
            raise Warning(_('Erreur!'), 
                        _('( %s ) : Cette valeur existe déja')% (values['taux_tva']))

        obj_id = super(taux_tva, self).create(values)
        return obj_id

    @api.multi
    def write(self, values):
        if values.get("default", False) == True:
            obj_ids = self.search([('default', '=', True)])
            if len(obj_ids) > 0:
                raise Warning(_('Erreur!'), 
                            _('Il faut un seul valeur par défaut'))
        #taux_tva doit etre unique
        if values.get("taux_tva", False) != False and values.get("taux_tva", False) != self.taux_tva:
            taux_tva_count  = self.search_count([('taux_tva', '=', values.get("taux_tva", False))])
            if taux_tva_count  > 0:
                raise Warning(_('Erreur!'), 
                            _('( %s ) : Cette valeur existe déja')% (values.get("taux_tva", False)))


        obj_id = super(taux_tva, self).write(values)
        return obj_id

#----------------------------------------------------------
# article_commande_rel 
#----------------------------------------------------------
class article_commande_rel(models.Model):

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_livre(self):
        for rec in self:
            qte = 0
            bl_ids = self.env['bon.livraison'].search([('commande_id', '=', rec.commande_id.id), 
                                                       ('article_id', '=', rec.article_id.id)])
            for bl in bl_ids:
                qte += bl.quantite
            self.quantite_livre = qte

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_reserve(self):
        for rec in self:
            qte = 0
            br_ids = self.env['bon.reservation'].search([('commande_id', '=', rec.commande_id.id), 
                                                         ('article_id', '=', rec.article_id.id)])
            for br in br_ids:
                qte += br.quantite
            self.quantite_reserve = qte

    @api.one
    @api.depends('quantite', 'quantite_livre')
    def _get_progress(self):
        if self.quantite > 0 and self.quantite_livre > 0:
            self.progress = self.quantite_livre / self.quantite * 100
        else:
            self.progress = 0

    _name = "article.commande.rel"

    article_id = fields.Many2one('production.article', 'Article', ondelete='cascade', required=True)
    commande_id = fields.Many2one('production.commande', 'Commande', ondelete='cascade', required=True)
    quantite = fields.Float('Quantité', required=True)
    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], related='article_id.unite', readonly=True, string='Unite')
    date_limit = fields.Date('Date limite', required=True)

    quantite_livre = fields.Float(compute='_get_quantite_livre', string='Qte_Livré')
    quantite_reserve = fields.Float(compute='_get_quantite_reserve', string='Qte_Rés')
    progress = fields.Float(compute='_get_progress', string='Progression')
    stock_non_reserve = fields.Float(string='Stk_Non_Rés', related='article_id.stock_non_reserve')

    @api.multi
    def creer_of(self):
        #pour creer un of il faut que la commande en etat demarre
        if self.commande_id.state != 'nonplanifie':
            raise Warning(_('Erreur!'),
                        _('OF est dejà Planifié'))
        return { 
            'name': _("Ordre fabrication"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'production.ordre.fabrication',
            'view_id': False,
            'context': {
                    'default_commande_id': self.commande_id.id, 
                    'default_article_sortant': self.article_id.id,
                    'default_quantite': self.quantite,
                    'default_date_fin': self.date_limit,
                    'default_line_commande_id': self.id,
                    'default_famille_id':self.article_id.famille_id.id,
                    'default_quantite':self.quantite
                    },
            }

    @api.multi
    def creer_bon_reservation(self):
        #pour creer un bon réservation il faut que la commande en etat demarre
        if self.commande_id.state == 'planifie':
            raise Warning(_('Erreur!'),
                        _('La commande  n\'est pas encore démarré'))
        return { 
            'name': _("Bon de réservation"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'bon.reservation',
            'view_id': False,
            'context': {
                    'default_client_id': self.commande_id.client_id.id, 
                    'default_commande_id': self.commande_id.id,
                    'default_article_id': self.article_id.id,
                    'default_quantite_commande': self.quantite
                    },
            }

    @api.multi
    def creer_bon_livraison(self):
        #pour creer un bon livraison il faut que la commande en etat demarre
        if self.commande_id.state == 'planifie':
            raise Warning(_('Erreur!'),
                        _('La commande  n\'est pas encore démarré'))
        return { 
            'name': _("Bon de livraison"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'bon.livraison',
            'view_id': False,
            'context': {
                    'default_client_id': self.commande_id.client_id.id, 
                    'default_commande_id': self.commande_id.id,
                    'default_article_id': self.article_id.id,
                    'default_quantite_commande': self.quantite
                    },
            }

#----------------------------------------------------------
# production_commande
#----------------------------------------------------------
class production_commande(models.Model):

    @api.one
    @api.depends('state')
    def _check_color(self):
        for rec in self:
            color = 0
            color_value = self.env['color.status'].search([('state', '=', rec.state)], limit=1).color
            if color_value:
                color = color_value

            self.member_color = color

    #button workflow Démarrer
    @api.one
    def action_demarrer_commande(self):
        if self.article_commande_ids:
            self.write({'state': 'demarre'})
        else:
            raise Warning(_('Erreur!'), 
                        _('Cette commande (%s) ne contient aucun article')% (self.num_commande))

    @api.one
    def action_confirmer_commande(self):
        self.write({'state': 'nonplanifie'})


    #button workflow Terminer
    @api.one
    def action_terminer_commande(self):
        self.write({'state': 'termine'})

    _name = 'production.commande'
    _rec_name = 'num_commande'

    member_color = fields.Integer(compute='_check_color', string='Color')
    of_ids = fields.One2many('production.ordre.fabrication', 'commande_id', 'Ordres de fabrication')
    num_commande = fields.Char('Num commande', required=True)
    client_id = fields.Many2one('vente.client', 'Client', required=True, ondelete='cascade')
    date_creation = fields.Date('Date création', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_limit_cmd = fields.Date('Date limite', required=True)
    article_commande_ids = fields.One2many('article.commande.rel', 'commande_id', 'Articles')
    state = fields.Selection([('nonconfirme','Non Confirmé'),('nonplanifie','Non Planifié'),('planifie','Planifié'),
                              ('demarre','Demarré'),
                              ('termine','Terminé')], 'Etat', readonly=True, default='nonconfirme')
    bon_livraison_ids = fields.One2many('bon.livraison', 'commande_id', 'Bons de livraiosn')
    bon_reservation_ids = fields.One2many('bon.reservation', 'commande_id', 'Bons de réservation')

    @api.model
    def create(self, values):
        #test num_commande doit etre unique
        if self.env['production.commande'].search_count([('num_commande', '=', values['num_commande'])]) > 0:
            raise Warning(_('Erreur!'),
                        _('Numéro commande existe déjà [ %s ].')% (values['num_commande']))

        # test date_creation <= date_limit_cmd
        if values['date_creation'] > values['date_limit_cmd']:
            raise Warning(_('Erreur!'),
                        _('Il faut que : Date création <= Date limite'))

        obj_id = super(production_commande, self).create(values)
        #test si les lignes articles sont distinct
        ids = []
        for obj in self.browse(obj_id.id):
            for line in obj.article_commande_ids:
                if line.article_id.id in ids:
                    raise Warning(_('Erreur!'), 
                                _("Même article ajouté plusieurs fois : %s") % line.article_id.code_article)
                ids.append(line.article_id.id)

        #récupérer les lignes de commande
        article_lines = self.env['article.commande.rel'].search([('commande_id', '=', obj_id.id)])
        for l in article_lines:
            #test date_creation <= date_limit (article) <= date_limit_cmd
            if l.date_limit > values['date_limit_cmd'] or l.date_limit < values['date_creation']:
                raise Warning(_('Erreur!'), 
                            _('Les dates des lignes articles doivent êtres dans [ %s , %s].\n %s qui est séléctionnée')% (values['date_creation'], values['date_limit_cmd'], l.date_limit))
            #vérifier quantité
            if float(l.quantite) <= 0:
                raise Warning(_('Erreur!'), 
                            _('La quantité doit être supérieur à zero'))

        return obj_id
    
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
                    'default_commande_id': self.id,
                    },
            }


    @api.multi
    def write(self, values):
        obj_id=super(production_commande,self).write(values)
        for obj in self:
            #test num_commande doit etre unique
            self.env.cr.execute('select * from production_commande where num_commande = %s',(obj.num_commande,))
            lines = self.env.cr.dictfetchall()

            if len(lines) > 1:
                raise Warning(_('Erreur!'), 
                            _('Numéro commande existe déjà [ %s ].')% (obj.num_commande))
            # test date_creation <= date_limit_cmd
            if obj.date_creation > obj.date_limit_cmd:
                raise Warning(_('Erreur!'), 
                            _('Il faut que : Date création <= Date limite'))

            #test si les lignes articles sont distinct
            ids = []
            for line in obj.article_commande_ids:
                if line.article_id.id in ids:
                    raise Warning(_('Erreur!'), 
                                _("Même article ajouté plusieurs fois : %s") % line.article_id.code_article)
                ids.append(line.article_id.id)

            #récupérer les lignes de commande
            article_lines = self.env['article.commande.rel'].search([('commande_id', '=', obj.id)])
            for l in article_lines:
                #test date_creation <= date_limit (article) <= date_limit_cmd
                if l.date_limit > obj.date_limit_cmd or l.date_limit < obj.date_creation:
                    raise Warning(_('Erreur!'), 
                                _('Les dates des lignes articles doivent êtres dans [ %s , %s].\n %s qui est séléctionnée')% (obj.date_creation, obj.date_limit_cmd, l.date_limit))
                #vérifier commande
                if float(l.quantite) <= 0:
                    raise Warning(_('Erreur!'), 
                                _('La quantité doit être supérieur à zero'))

        return obj_id

#----------------------------------------------------------
# bon_reservation
#----------------------------------------------------------
class bon_reservation(models.Model):

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_commande(self):
        qte = 0
        if self.commande_id and self.article_id:
            self.quantite_commande = self.env['article.commande.rel'].search([('article_id', '=', self.article_id.id), 
                                                                              ('commande_id', '=', self.commande_id.id)], 
                                                                              limit=1).quantite

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_livre(self):
        qte = 0
        if self.commande_id and self.article_id:
            bon_livraison_ids = self.env['bon.livraison'].search([('commande_id', '=', self.commande_id.id), 
                                                                  ('article_id', '=', self.article_id.id)])
            for bl in bon_livraison_ids:
                qte += bl.quantite

        self.quantite_livre = qte

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_reserve(self):
        qte = 0
        if self.commande_id and self.article_id:
            bon_reservation_ids = self.env['bon.reservation'].search([('commande_id', '=', self.commande_id.id), 
                                                                      ('article_id', '=', self.article_id.id)])
            for br in bon_reservation_ids:
                qte += br.quantite

        self.quantite_reserve = qte

    @api.one
    @api.depends('quantite_commande', 'quantite_reserve')
    def _get_progress_reserve_commande(self):
        if self.quantite_commande > 0 and self.quantite_reserve > 0:
            self.progress_reserve_commande = self.quantite_reserve / self.quantite_commande * 100
        else:
            self.progress_reserve_commande = 0

    _name = 'bon.reservation'

    code_bon = fields.Char('Code bon :', readonly=True)
    date_bon = fields.Date('Date bon', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
    client_id = fields.Many2one('vente.client', 'Code client', ondelete='cascade', required=True, domain=[('id', 'in', [])])
    commande_id = fields.Many2one('production.commande', 'Code commande', ondelete='cascade', required=True,    
                                    domain="[('state', '=', 'demarre')]" )
    article_id = fields.Many2one('production.article', 'Code article', ondelete='cascade', required=True)
    quantite = fields.Float('Quantité ', required=True)
    #ajouter qte satisfaite= 
    remarque = fields.Text('Remarque')

    quantite_commande = fields.Float(compute='_get_quantite_commande', string='Quantité commandé')
    quantite_livre = fields.Float(compute='_get_quantite_livre', string='Quantité livré')
    quantite_reserve = fields.Float(compute='_get_quantite_reserve', string='Quantité réservé')

    stock_disponible = fields.Float('Stock disponible', related='article_id.stock_disponible')
    stock_non_reserve = fields.Float('Stock non réservé', related='article_id.stock_non_reserve')

    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], related='article_id.unite', readonly=True, string='Unite')
    progress_reserve_commande = fields.Float(compute='_get_progress_reserve_commande', string='Progression quantité réservé')

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(bon_reservation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'article_id':
                res['fields'][field]['domain'] = [('id','in', [])]

        return res

    @api.model
    def create(self, values):
        #test si quantite <= 0 on genere exception
        if values['quantite'] <= 0:
            raise Warning(_('Erreur!'), 
                        _('La quantité doit étre supérieur strictement à zero ( %s )')% (values['quantite']))

        #test si quantite à réservé > stock_non_réservé ==> exception
        article_obj = self.env['production.article'].browse(values['article_id'])
        if values['quantite'] > article_obj.stock_non_reserve:
            raise Warning(_('Erreur!'), 
                        _('La quantité à réservé est supérieur à la quantité stock disponible'))

        #Trouver quantité commandé
        values['quantite_commande'] = self.env['article.commande.rel'].search([('article_id', '=', values['article_id']), 
                                                                            ('commande_id', '=', values['commande_id'])], 
                                                                            limit=1).quantite

        #Calcul quantite réservé
        bon_reservation_ids = self.env['bon.reservation'].search([('commande_id', '=', values['commande_id']), 
                                                                  ('article_id', '=', values['article_id'])])
        qte_reserve = 0
        for b in bon_reservation_ids:
            qte_reserve += b.quantite

        #test si quantite réservé > quantite commandé ==> exception
        qte_reserve_total = qte_reserve + values['quantite']
        if qte_reserve_total > values['quantite_commande']:
            raise Warning(_('Erreur!'), 
                        _('La quantité à réservé est supérieur à la quantité demandé :\n \
                         (qantite_à_réservé : %s / quantite_demandé : %s)')% (qte_reserve_total, values['quantite_commande']))

        #augmenter le stock_reserve
        article_obj.stock_reserve += values['quantite']

        #generer code sequence "code_bon"
        values['code_bon'] = self.env['ir.sequence'].get('bon.reservation')

        new_id = super(bon_reservation, self).create(values)
        return new_id

    @api.multi
    def write(self, values):

        nouv_article = values.get('article_id', None)
        nouv_quantite = values.get('quantite', None)
        ancien_article_obj = self.env['production.article'].browse(self.article_id.id)

        if nouv_article:
            nouv_article_obj = self.env['production.article'].browse(nouv_article)
            #si il y a une nouvelle quantité
            if nouv_quantite:
                #test si quantite <= 0 on genere exception
                if nouv_quantite <= 0:
                    raise Warning(_('Erreur!'), 
                                _('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

                #test si quantite à réservé > stock_non_réservé ==> exception
                if nouv_quantite > nouv_article_obj.stock_non_reserve:
                    raise Warning(_('Erreur!'), 
                                _('La quantité à réservé est supérieur à la quantité stock disponible'))

                #modifier le stock
                ancien_article_obj.stock_reserve -= self.quantite
                nouv_article_obj.stock_reserve += nouv_quantite

            else:#meme quantite
                #test si quantite à réservé > stock_non_réservé ==> exception
                if self.quantite > nouv_article_obj.stock_non_reserve:
                    raise Warning(_('Erreur!'), 
                                _('La quantité à réservé est supérieur à la quantité stock disponible'))

                #modifier le stock
                ancien_article_obj.stock_reserve -= self.quantite
                nouv_article_obj.stock_reserve += self.quantite
        else:
            if nouv_quantite:
                #test si quantite <= 0 on genere exception
                if nouv_quantite <= 0:
                    raise Warning(_('Erreur!'), 
                                _('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

                #test si quantite à réservé > stock_non_réservé ==> exception
                if (nouv_quantite - self.quantite) > ancien_article_obj.stock_non_reserve:
                    raise Warning(_('Erreur!'), 
                                _('La quantité à réservé est supérieur à la quantité stock disponible'))

                #modifier le stock
                ancien_article_obj.stock_reserve += nouv_quantite - self.quantite

        obj_id=super(bon_reservation, self).write(values)

        return obj_id

    @api.multi
    def unlink(self):
        for rec in self:
            article_obj = self.env['production.article'].browse(rec.article_id.id)
            article_obj.stock_reserve -= rec.quantite

        return super(bon_reservation, self).unlink()


    @api.onchange('commande_id')
    def onchange_commande_id(self):
        res = {}
        ids = []
        default_commande = self._context.get('default_commande_id', False)
        default_article = self._context.get('default_article_id', False)
        if self.commande_id:
            if default_article == False:
                self.article_id = []
            if default_commande:
                if self.commande_id.id != default_commande:
                    self.article_id = []
            #filter sur le champ article_id selon commande_id séléctionné
            for ligne in self.commande_id.article_commande_ids:
                ids.append(ligne.article_id.id)

            #select client_id selon commande_id séléctionné
            self.client_id = self.commande_id.client_id

        else:#si commande_id vide
            self.article_id = []

        res['domain'] = {'article_id': [('id', 'in', ids)]}

        return res

#----------------------------------------------------------
# bon_livraison
#----------------------------------------------------------
class bon_livraison(models.Model):

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_commande(self):
        qte = 0
        if self.commande_id and self.article_id:
            self.quantite_commande = self.env['article.commande.rel'].search([('article_id', '=', self.article_id.id), 
                                                                              ('commande_id', '=', self.commande_id.id)], 
                                                                              limit=1).quantite

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_livre(self):
        qte = 0
        if self.commande_id and self.article_id:
            bon_livraison_ids = self.env['bon.livraison'].search([('commande_id', '=', self.commande_id.id), 
                                                                  ('article_id', '=', self.article_id.id)])
            qte = 0
            for bl in bon_livraison_ids:
                qte += bl.quantite

        self.quantite_livre = qte

    @api.one
    @api.depends('commande_id', 'article_id')
    def _get_quantite_reserve(self):
        qte = 0
        if self.commande_id and self.article_id:
            bon_reservation_ids = self.env['bon.reservation'].search([('commande_id', '=', self.commande_id.id), 
                                                                      ('article_id', '=', self.article_id.id)])
            qte = 0
            for br in bon_reservation_ids:
                qte += br.quantite

        self.quantite_reserve = qte

    @api.one
    @api.depends('quantite_commande', 'quantite_livre')
    def _get_progress_livre_commande(self):
        if self.quantite_commande > 0 and self.quantite_livre > 0:
            self.progress_livre_commande = self.quantite_livre / self.quantite_commande * 100
        else:
            self.progress_livre_commande = 0

    @api.one
    @api.depends('quantite_commande', 'quantite_reserve')
    def _get_progress_reserve_commande(self):
        if self.quantite_commande > 0 and self.quantite_reserve > 0:
            self.progress_reserve_commande = self.quantite_reserve / self.quantite_commande * 100
        else:
            self.progress_reserve_commande = 0

    _name = 'bon.livraison'

    code_bon = fields.Char('Code bon :', readonly=True)
    date_bon = fields.Date('Date bon', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
    client_id = fields.Many2one('vente.client', 'Code client', ondelete='cascade', required=True, domain=[('id', 'in', [])])
    commande_id = fields.Many2one('production.commande', 'Code commande', ondelete='cascade', required=True, 
                                    domain="[('state', '=', 'demarre')]" )
    article_id = fields.Many2one('production.article', 'Code article', ondelete='cascade', required=True)
    quantite = fields.Float('Quantité', required=True)

    quantite_commande = fields.Float(compute='_get_quantite_commande', string='Quantité commandé')
    quantite_commande2 = fields.Float('Quantité commandé', related='quantite_commande')
    quantite_livre = fields.Float(compute='_get_quantite_livre', string='Quantité livré')
    quantite_reserve = fields.Float(compute='_get_quantite_reserve', string='Quantité réservé')
    stock_disponible = fields.Float('Stock disponible', related='article_id.stock_disponible')
    stock_non_reserve = fields.Float('Stock non réservé', related='article_id.stock_non_reserve')

    unite = fields.Selection([('u','U'),
                              ('kg','Kg'),
                              ('m2','m²'),
                              ('m','m')], related='article_id.unite', readonly=True, string='Unite')
    progress_reserve_commande = fields.Float(compute='_get_progress_reserve_commande', string='Progression quantité réservé')
    progress_livre_commande = fields.Float(compute='_get_progress_livre_commande', string='Progression quantité livré')

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(bon_livraison, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        for field in res['fields']:
            if field == 'article_id':
                res['fields'][field]['domain'] = [('id','in', [])]

        return res

    @api.model
    def create(self, values):
        #test si quantite <= 0 on genere exception
        if values['quantite'] <= 0:
            raise Warning(_('Erreur!'), 
                        _('La quantité doit étre supérieur strictement à zero ( %s )')% (values['quantite']))

        #Calcul quantite réservé
        bon_reservation_ids = self.env['bon.reservation'].search([('commande_id', '=', values['commande_id']), 
                                                                ('article_id', '=', values['article_id'])])
        qte_res = 0
        for b in bon_reservation_ids:
            qte_res += b.quantite

        #test si aucun quantite réservé
        if qte_res == 0:
            raise Warning(_('Erreur!'), 
                        _('Aucun quantité réservé dans le stock'))

        #Calcul quantite livré
        bon_livraison_ids = self.env['bon.livraison'].search([('commande_id', '=', values['commande_id']), 
                                                              ('article_id', '=', values['article_id'])])
        qte_livre = 0
        for b in bon_livraison_ids:
            qte_livre += b.quantite

        #test si quantite livre > quantite reserve ==> exception
        qte_livre_total = qte_livre + values['quantite']
        if qte_livre_total > qte_res:
            raise Warning(_('Erreur!'), 
                        _('La quantité à livrer est supérieur à la quantité réservé:\n \
                        (quantite_à_livré : %s / quantite_réservé : %s)')% (qte_livre_total, qte_res))

        #generer code sequence "code_bon"
        values['code_bon'] = self.env['ir.sequence'].get('bon.livraison')

        # stock_reel -= qte
        # stock_reserve -= qte
        article_obj = self.env['production.article'].browse(values['article_id'])
        if article_obj:
            article_obj.stock_reel -= values['quantite']
            article_obj.stock_reserve -= values['quantite']

            #test stock minimale
            article_obj.verifier_stock()

        new_id = super(bon_livraison, self).create(values)

        return new_id

    @api.multi
    def write(self, values):

        commande = values.get('commande_id', None)
        if commande == None:
            commande = self.commande_id.id
        nouv_article = values.get('article_id', None)
        nouv_quantite = values.get('quantite', None)
        ancien_article_obj = self.env['production.article'].browse(self.article_id.id)

        if nouv_article:
            #Calcul quantite réservé
            bon_reservation_ids = self.env['bon.reservation'].search([('commande_id', '=', commande), 
                                                                    ('article_id', '=', nouv_article)])
            qte_res = 0
            for b in bon_reservation_ids:
                qte_res += b.quantite

            #Calcul quantite livré
            bon_livraison_ids = self.env['bon.livraison'].search([('commande_id', '=', commande), 
                                                                  ('article_id', '=', nouv_article)])
            qte_livre = 0
            for b in bon_livraison_ids:
                qte_livre += b.quantite

            nouv_article_obj = self.env['production.article'].browse(nouv_article)
            #si il y a une nouvelle quantité
            if nouv_quantite:
                #test si quantite <= 0 on genere exception
                if nouv_quantite <= 0:
                    raise Warning(_('Erreur!'), 
                                _('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

                #test si quantite livre > quantite reserve ==> exception
                qte_livre_total = qte_livre + nouv_quantite
                if qte_livre_total > qte_res:
                    raise Warning(_('Erreur!'), 
                                _('La quantité à livrer est supérieur à la quantité réservé:\n \
                                (quantite_à_livré : %s / quantite_réservé : %s)')% (qte_livre_total, qte_res))


                #modifier le stock
                ancien_article_obj.stock_reel += self.quantite
                ancien_article_obj.stock_reserve += self.quantite
                nouv_article_obj.stock_reel -= nouv_quantite
                nouv_article_obj.stock_reserve -= nouv_quantite

            else:#meme quantite
                #test si quantite livre > quantite reserve ==> exception
                qte_livre_total = qte_livre + self.quantite
                if qte_livre_total > qte_res:
                    raise Warning(_('Erreur!'), 
                                _('La quantité à livrer est supérieur à la quantité réservé:\n \
                                (quantite_à_livré : %s / quantite_réservé : %s)')% (qte_livre_total, qte_res))

                #modifier le stock
                ancien_article_obj.stock_reel += self.quantite
                ancien_article_obj.stock_reserve += self.quantite
                nouv_article_obj.stock_reel -= self.quantite
                nouv_article_obj.stock_reserve -= self.quantite
        else:
            if nouv_quantite:
                #test si quantite <= 0 on genere exception
                if nouv_quantite <= 0:
                    raise Warning(_('Erreur!'), 
                                _('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

                #Calcul quantite réservé
                bon_reservation_ids = self.env['bon.reservation'].search([('commande_id', '=', commande), 
                                                                        ('article_id', '=', self.article_id.id)])
                qte_res = 0
                for b in bon_reservation_ids:
                    qte_res += b.quantite

                #Calcul quantite livré
                bon_livraison_ids = self.env['bon.livraison'].search([('commande_id', '=', commande), 
                                                                      ('article_id', '=', self.article_id.id)])
                qte_livre = 0
                for b in bon_livraison_ids:
                    qte_livre += b.quantite

                #test si quantite livre > quantite reserve ==> exception
                if nouv_quantite > self.quantite:
                    qte_livre_total = qte_livre + nouv_quantite - self.quantite
                    if qte_livre_total > qte_res:
                        raise Warning(_('Erreur!'), 
                                    _('La quantité à livrer est supérieur à la quantité réservé:\n \
                                    (quantite_à_livré : %s / quantite_réservé : %s)')% (qte_livre_total, qte_res))

                #modifier le stock
                ancien_article_obj.stock_reel += self.quantite - nouv_quantite
                ancien_article_obj.stock_reserve += self.quantite - nouv_quantite


        obj_id=super(bon_livraison,self).write(values)

        return obj_id


    @api.multi
    def unlink(self):
        for rec in self:
            article_obj = self.env['production.article'].browse(rec.article_id.id)
            article_obj.stock_reel += rec.quantite
            article_obj.stock_reserve += rec.quantite

        return super(bon_livraison, self).unlink()
    
    

    @api.onchange('commande_id')
    def onchange_commande_id(self):
        res = {}
        ids = []
        default_commande = self._context.get('default_commande_id', False)
        default_article = self._context.get('default_article_id', False)
        if self.commande_id:
            if default_article == False:
                self.article_id = []
            if default_commande:
                if self.commande_id.id != default_commande:
                    self.article_id = []
            #filter sur le champ article_id selon commande_id séléctionné
            for ligne in self.commande_id.article_commande_ids:
                ids.append(ligne.article_id.id)

            #select client_id selon commande_id séléctionné
            self.client_id = self.commande_id.client_id

        else:#si commande_id vide
            self.article_id = []

        res['domain'] = {'article_id': [('id', 'in', ids)]}
        return res

