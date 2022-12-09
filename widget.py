from btss.widgets import *
from .task import GoNoGratingsOriTask

class GoNoGratingsOriWidget(QWidget):
    def __init__(self,task):
        super(GoNoGratingsOriWidget,self).__init__()
        self.task = task
        self.rig = task.rig
        lay = QGridLayout()
        self.setLayout(lay)
        self.tmaxpsychplot = 15*60 # seconds
        self.ntrialstoplot = 80
        self.fig = plt.figure(figsize=(3, 3))
        self.canvas = FigureCanvas(self.fig)
        self.canvas_widget = QWidget()
        l = QVBoxLayout()
        l.addWidget(NavigationToolbar(self.canvas, self.canvas_widget))
        l.addWidget(self.canvas)
        self.canvas_widget.setLayout(l)
        self._init_figure()
        ####################REWARD######################
        r = QGroupBox('Spouts - Reward')
        l = QFormLayout(r)
        r.setLayout(l)
        rewardvol = WidQFloat(label = 'Reward volume',
                              value = self.task.reward_volume,
                              vmin = 0.5,
                              vmax = 20)
        rewardvol.spin.setSingleStep(0.1)
        def _rewardvol():
            self.task.reward_volume = float(rewardvol.val())
            if not self.task.rig is None:
                # button gives only a fraction of the reward
                frac = 0.6
                self.rig.set_water_volume(valve0 = self.task.reward_volume[0]*frac)
        rewardvol.link(_rewardvol)
        reward = QPushButton('reward')
        reward.resize(40,20)
        def _reward():
            _rewardvol()
            self.task._give_reward(0,flipandwait=True)
        reward.clicked.connect(_reward)
        
        l.addRow(reward)
        l.addRow(rewardvol)
        
        lay.addWidget(r,0,0,1,1)

        ####################TASK######################
        w = QGroupBox('Task settings')
        l = QFormLayout()
        w.setLayout(l)
        lay.addWidget(w,1,0,1,1)
            
        self.wstate = QLabel('')
        l.addRow(self.wstate)
        
        pause = QCheckBox()
        def _pause(value):
            self.task.pause = value>0
        pause.stateChanged.connect(_pause)
        
        p = QWidget()
        pp = QFormLayout()
        p.setLayout(pp)
        pp.addRow(QLabel('Pause'),pause)
        # probability left
        self.pgo = WidQFloat(label = 'Prob go',
                             value = self.task.prob_go,
                             vmin = 0,
                             vmax = 1)
        self.pgo.spin.setSingleStep(0.1)
        self.pgo.link(self._pgo)
        l.addRow(p, self.pgo)
        
        self.settings = dict(inter_trial_interval = "inter_trial_interval",
                             response_period = "response_period",
                             post_reward_duration = "post_reward_duration",
                             nlicks_to_reward = "nlicks_to_reward",
                             audio_volume = "audio_volume",
                             punishment_duration = "punishment_cue['duration']",
                             trial_cue_frequency = "trial_cue['frequency']",
                             trial_cue_duration = "trial_cue['duration']",
                             reward_cue_frequency = "reward_cue['frequency']",
                             reward_cue_duration = "reward_cue['duration']")

        settingwid = WidQCombo("Setting:",list(self.settings.keys()),list(self.settings.keys())[-1])
        settingedit = QLineEdit('')
        def _settingwid(ind):
            t = list(self.settings.keys())[ind]
            value = eval("self.task.{0}".format(self.settings[t]))
            if not value is None:
                if type(value) in [int,float,bool]:
                    val = str(value)
                elif type(value) is str:
                    val = "'"+value+"'"
                else:
                    val = '['+','.join([str(s) for s in value])+']'
            else:
                val = 'None'
            settingedit.setText(val)
        _settingwid(-1)
        settingwid.link(_settingwid)
        def _settingedit():
            val = settingedit.text()
            val = val.strip(' ')
            idx = settingwid.combo.currentIndex()
            t = list(self.settings.keys())[idx]
            try:
                if len(val):
                    print("self.task.{0} = {1}".format(self.settings[t],val))
                    exec("self.task.{0} = {1}".format(self.settings[t],val))
            except Exception as e:
                print(e)
        settingedit.textChanged.connect(_settingedit)
                
        l.addRow(settingwid)
        l.addRow(QLabel('Setting values:'),settingedit)
    def _pgo(self):
        self.task.prob_go = self.pgo.val()
        self.task.redraw_trials = True

    def set_state(self,state):
        self.wstate.setText('state: <b> {0} </b> - trial time: {1:.3f}s '.format(
            state, self.task.trial_clock.getTime()))
        
    def trial_init_update(self):
        m = np.max([0,self.task.itrial-self.ntrialstoplot])
        mm = np.min([len(self.task.trial_list), self.task.itrial+25])
        
        y = self.task.trial_list[m:mm]
        x = np.arange(m,mm)

        self.ptrial['all'].set_xdata(x)
        self.ptrial['all'].set_ydata(y)
        self.ptrial['itrial'].set_xdata([self.task.itrial,self.task.itrial])
        if self.task.itrial >= 1:
            nrewards = np.sum(self.task.task_trial_data.rewarded)
            self.pntrials['nrewards'].set_height(nrewards)
            self.pntrials['nrewards'].set_y(0)
            self.pntrials['water'].set_text('${0:1.2f} ml$'.format(np.sum(self.task.task_trial_data.rewarded*self.task.task_trial_settings.reward_volume)/1000.))
            self.pntrials['water'].set_position((3,0))

            sel = self.task.task_trial_data.iloc[m:].copy()
            sel['y'] = self.task.trial_list[m:self.task.itrial]
            
            nx_r = sel.itrial[sel.rewarded>0].values
            ny_r = sel.y[sel.rewarded>0].values
            nx_p = sel.itrial[(sel.rewarded==0) & ~(sel.response==0)].values
            ny_p = sel.y[(sel.rewarded==0) & ~(sel.response==0)].values

            self.ptrial['rewarded'].set_xdata(nx_r)
            self.ptrial['rewarded'].set_ydata(ny_r)
            self.ptrial['punished'].set_xdata(nx_p)
            self.ptrial['punished'].set_ydata(ny_p)
        
            ntotal = len(self.task.task_trial_data)
            self.pntrials['all'].set_height(ntotal)
                           
            if len(sel) >= 2:
                # select only the last n seconds
                ns = sel[sel.task_start_time>(sel.task_start_time.iloc[-1] - self.tmaxpsychplot)]
                #self.h['axpsych'].set_xlim([0,2])
            self.h['axntrials'].set_ylim([0, int(self.task.itrial)])
            self.h['axtrial'].set_xlim([m, mm])
        self.canvas.draw()

    def trial_end_update(self):
        pass

    def _init_figure(self):
        self.h = {}
        self.h['fig'] = self.fig
        self.h['axtrial'] = self.h['fig'].add_axes([0.15,0.9,0.8,0.05])
        self.h['axtrial'].set_yticks([0,1])
        self.h['axtrial'].set_yticklabels(['L','R'])
        self.h['axtrial'].set_xlabel('Trial')
        self.h['axtrial'].spines['top'].set_visible(False)
        self.h['axtrial'].spines['right'].set_visible(False)
        self.h['axtrial'].set_ylim([-0.2,1.2])
        self.ptrial = dict(all = self.h['axtrial'].plot([],[],'o',
                                                        markerfacecolor='none',
                                                        markersize = 4)[0],
                           rewarded = self.h['axtrial'].plot([],[], 'o',
                                                             color = colors[3],markersize = 4)[0],
                           punished = self.h['axtrial'].plot([],[], 'o',
                                                             color = colors[0],markersize = 4)[0],
                           itrial = self.h['axtrial'].plot([0,0],[0,1], 'r--')[0],)
        
        self.h['axpsych'] = self.h['fig'].add_axes([0.2,0.2,0.3,0.5])
        self.h['axpsych'].set_xlabel('Stim intensity',fontsize = 9)
        self.h['axpsych'].set_ylabel('P$_{LEFT}$',fontsize = 9)
        self.h['axpsych'].spines['top'].set_visible(False)
        self.h['axpsych'].spines['right'].set_visible(False)
        self.h['axpsych'].set_ylim([0,1])

        
        self.ppsych = {'trial' : self.h['axpsych'].plot([],[],'.--',
                                                         clip_on = False,
                                                         color=colors[0])[0],
                       'total' : self.h['axpsych'].plot([],[],'.--',
                                                        clip_on = False,
                                                        color=colors[1])[0]}
        self.h['axpsych'].legend([self.ppsych['trial'],
                                  self.ppsych['total']],
                                 ['trial','all'],fontsize='x-small',
                                 frameon=False,fancybox=True, framealpha=0.5)
        
        self.h['axntrials'] = self.h['fig'].add_axes([0.7,0.2,0.2,0.5])
        self.h['axntrials'].set_ylabel('# trials')
        self.h['axntrials'].spines['top'].set_visible(False)
        self.h['axntrials'].spines['right'].set_visible(False)
        self.pntrials = dict(all = self.h['axntrials'].bar(
                                 0,height = 0,bottom = 0,width = 0.8, color = 'k')[0],
                             left_r = self.h['axntrials'].bar(
                                 1,height = 0,bottom = 0,width = 0.8, color = colors[3])[0],
                             left_n = self.h['axntrials'].bar(
                                 1,height = 0,bottom = 0,width = 0.8, color = [.5,.5,.5])[0],
                             left_p = self.h['axntrials'].bar(
                                1,height = 0,bottom = 0,width = 0.8, color = colors[0])[0],
                             right_r = self.h['axntrials'].bar(
                                 2,height = 0,bottom = 0,width = 0.8, color = colors[3])[0],
                             right_n = self.h['axntrials'].bar(
                                 2,height = 0,bottom = 0,width = 0.8, color = [.5,.5,.5])[0],
                             right_p = self.h['axntrials'].bar(
                                 2,height = 0,bottom = 0,width = 0.8, color = colors[0])[0],
                             nrewards = self.h['axntrials'].bar(
                                 3,height = 0,bottom = 0,width = 0.8, color = colors[1])[0],
                             water = self.h['axntrials'].text(3,0,'0 ml',
                                                              va = 'bottom',
                                                              ha = 'center',
                                                              rotation = 90))
        self.h['axntrials'].set_xticks([0,1,2,3])
        self.h['axntrials'].set_xticklabels(['all','left','right','rewards'],
                                            rotation = 90,
                                            fontsize = 9)
 

