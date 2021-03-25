

openerp.production = function (instance) {
    //widget qte_stock
    instance.web.list.columns.add('field.qte_stock', 'instance.production.qte_stock');
    instance.production.qte_stock = instance.web.list.Column.extend({
        _format: function (row_data, options) {
            res = this._super.apply(this, arguments);
            var amount = parseFloat(res);
            if (amount <= 0){
                return "<font color='#ff0000'>"+(amount)+"</font>";
            }
            return res
        }
    });

//    instance.web.form.widgets.add('formule', 'instance.web.form.formulewidget');
//    instance.web.form.formulewidget = instance.web.form.widgets.extend({
//        alert("test if widget is called");
//    });

    instance.web.form.widgets.add('formule', 'instance.production.formulewidget');
    instance.production.formulewidget = instance.web.form.FieldChar.extend(
    {
        template : "formule",
        events: {
            'change input': 'store_dom_value',
        },
        init: function (view, code) {
            this._super(view, code);
        },
        render_value: function() {
            var show_value = this.format_value(this.get('value'), '');
            if (!this.get("effective_readonly")) {
                this.$el.find('input').val(show_value);
            } else {
                if (this.password) {
                    show_value = new Array(show_value.length + 1).join('*');
                }
                this.$(".oe_form_char_content").text(show_value);
            }
        },
        store_dom_value: function () {
            if (!this.get('effective_readonly')
                    && this.$('input').length
                    && this.is_syntax_valid()) {
                this.internal_set_value(
                    this.parse_value(
                        this.$('input').val()));
            }
        },
        is_syntax_valid: function() {
            if (!this.get("effective_readonly") && this.$("input").size() > 0) {
                try {
                    this.parse_value(this.$('input').val(), '');

		    var qs = 1, pu = 1, mc = 1, pl = 1, d = 1, dl = 1, mt = 1, ml = 1, la = 1, lo = 1, nl = 1, nt = 1;
		    var q1 = 1, pu1 = 1, mc1 = 1, pl1 = 1, d1 = 1, dl1 = 1, mt1 = 1, ml1 = 1, la1 = 1, lo1 = 1, nl1 = 1, nt1 = 1;
		    var q2 = 1, pu2 = 1, mc2 = 1, pl2 = 1, d2 = 1, dl2 = 1, mt2 = 1, ml2 = 1, la2 = 1, lo2 = 1, nl2 = 1, nt2 = 1;
		    if(this.$('input').val() != '') {
		        var result = eval('(' + this.$('input').val() + ')');
		    }
/*
		    this._model = new instance.web.Model("production.famille.entrant.param");
		    console.log("... ... ... ... ... ... ... ... ... val ... " + this.$('input').val());
		    var x = this._model.call('test_formule',[[],this.$('input').val()])
					.done(function(results){ 
					    console.log("... ... ... ... ... ... ... ... ... res ... " + results);
					});
*/
		    return true;
                } catch(e) {
                    return false;
                }
            }
            return true;
        },
        parse_value: function(val, def) {
            return instance.web.parse_value(val, this, def);
        },

    });


};

/*
openerp.production = function(instance){

    var QWeb = openerp.web.qweb;
        _t = instance.web._t;
    instance.web.FormView.include({
    //instance.web.FormView.include({
        load_form: function(data) {
	    this._super(data);
            var self = this;
            //this.$el.find('#aa').blur(function() {
            this.$('#formule').blur(function() {
		alert( "oooo" );
		//$('#unite_q1').hide();
            });
        },

    });
};
*/
/*
openerp.production = function(instance) {

    var QWeb = openerp.web.qweb;
        _t = instance.web._t;

    instance.web.FormView.include({
        load_form: function(data) {
            var self = this;
            this.$el.find('#nom').on('blur', function() {
                alert( this.value ); // or $(this).val()
            });
            return self._super(data);
        },

    });
};
*/
/*

	var x = document.getElementById("famille");
	x.addEventListener("focus", myFocusFunction, true);
	x.addEventListener("blur", myBlurFunction, true);

	function myFocusFunction() {
	    document.getElementById("catdescription").style.backgroundColor = "yellow";
	}

	function myBlurFunction() {
	    document.getElementById("catdescription").style.backgroundColor = "";
	}
*/



