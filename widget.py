from btss.widgets import *
from .task import GoNoGratingsOriTask

class GoNoGratingsOriWidget(QWidget):
    def __init__(self,task):
        super(GoNoGratingsOriWidget,self).__init__()
        self.task = task
        self.rig = task.rig
        self.motors_par = self.task.motors_par
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
        ####################MOTORS######################
        w = QGroupBox('Motor control')
        #l = QFormLayout(w)
        l = QGridLayout(w)
        w.setLayout(l)
        mout0 = WidQInt(label = 'Left out',
                        value = int(self.task.motors_par['position_out'][0]),
                        vmin = -30,
                        vmax = 30)
        def _out():
            self.rig.set_motors(*self.task.motors_par['position_out'])
        def _in():
            self.rig.set_motors(*self.task.motors_par['position_in'])
        def _mout0():
            self.task.motors_par['position_out'][0] = mout0.val()
            _out()
        mout0.link(_mout0)
        mout1 = WidQInt(label = 'Right out',
                        value = int(self.task.motors_par['position_out'][1]),
                        vmin = -30,
                        vmax = 30)
        def _mout1():
            self.task.motors_par['position_out'][1] = mout1.val()
            _out()
        mout1.link(_mout1)
        
        l.addWidget(mout0,0,0,1,1)
        l.addWidget(mout1,0,1,1,1)
        min0 = WidQInt(label = 'Left in',
                        value = int(self.task.motors_par['position_in'][0]),
                        vmin = -30,
                        vmax = 30)
        def _min0():
            self.task.motors_par['position_in'][0] = min0.val()
            _in()
            
        min0.link(_min0)
        min1 = WidQInt(label = 'Right in',
                        value = int(self.task.motors_par['position_in'][1]),
                        vmin = -30,
                        vmax = 30)
        def _min1():
            self.task.motors_par['position_in'][1] = min1.val()
            _in()
        min1.link(_min1)
        l.addWidget(min0,1,0,1,1)
        l.addWidget(min1,1,1,1,1)
        
        m_out = QPushButton('out')
        
        m_in = QPushButton('in')
        
        m_in.clicked.connect(_in)
        m_out.clicked.connect(_out)
        l.addWidget(m_in,2,0,1,1)
        l.addWidget(m_out,2,1,1,1)

        ####################REWARD######################
        r = QGroupBox('Spouts - Reward')
        l = QFormLayout(r)
        r.setLayout(l)
        rewardvol = WidQFloat(label = 'Reward volume',
                              value = self.task.reward_volume[0],
                              vmin = 0.5,
                              vmax = 6)
        rewardvol.spin.setSingleStep(0.1)
        def _rewardvol():
            self.task.reward_volume = [float(rewardvol.val())]*2
            if not self.task.rig is None:
                # button gives only a fraction of the reward
                frac = 0.6
                self.rig.set_water_volume(valve0 = self.task.reward_volume[0]*frac,
                                          valve1 = self.task.reward_volume[1]*frac)
        rewardvol.link(_rewardvol)
        reward_left = QPushButton('Left')
        reward_left.resize(40,20)
        def _rewardleft():
            _rewardvol()
            self.task._give_reward(0,flipandwait=True)
        reward_right = QPushButton('Right')
        reward_right.resize(40,20)
        def _rewardright():
            _rewardvol()
            self.task._give_reward(1,flipandwait=True)
        reward_right.clicked.connect(_rewardright)
        reward_left.clicked.connect(_rewardleft)
        
        l.addRow(reward_left,reward_right)
        l.addRow(rewardvol)
        
        lay.addWidget(w,0,0,1,1)
        lay.addWidget(r,1,0,1,1)

        ####################TASK######################
        w = QGroupBox('Task settings')
        l = QFormLayout()
        w.setLayout(l)
        lay.addWidget(w,0,1,2,1)
            
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
        self.pleft = WidQFloat(label = 'Prob left',
                               value = self.task.prob_left,
                               vmin = 0,
                               vmax = 1)
        self.pleft.spin.setSingleStep(0.1)
        self.pleft.link(self._pleft)
        l.addRow(p, self.pleft)
        
        self.settings = dict(block_exit_ntrials = "block_par['ntrials_exit_criteria']",
                             block_exit_performance = "block_par['performance_exit']",
                             block_probabilities = "block_par['probabilities']",
                             inter_trial_interval = "inter_trial_interval",
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
    def _pleft(self):
        self.task.prob_left = self.pleft.val()
        self.task.redraw_trials = True

    def set_state(self,state):
        self.wstate.setText('state: <b> {0} </b> - trial time: {1:.3f}s - <b>{2}</b>'.format(
            state, self.task.trial_clock.getTime(),self.task.current_block_side))
        
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
            # left
            ileft = np.where(sel.rewarded_side_index.values == 1)
            selleft = sel.iloc[ileft]
            left_n = np.sum(selleft.response == 0)
            left_r = np.sum(selleft.response == 1)
            left_p = np.sum(selleft.response == -1)
            self.pntrials['left_p'].set_height(left_p)
            self.pntrials['left_p'].set_y(0)
            self.pntrials['left_n'].set_height(left_n)
            self.pntrials['left_n'].set_y(left_p)
            self.pntrials['left_r'].set_height(left_r)
            self.pntrials['left_r'].set_y(left_n+left_p)            
            iright = np.where(sel.rewarded_side_index.values == -1)
            selright = sel.iloc[iright]
            right_n = np.sum(selright.response == 0)
            right_r = np.sum(selright.response == -1)
            right_p = np.sum(selright.response == 1)
            self.pntrials['right_p'].set_height(right_p)
            self.pntrials['right_p'].set_y(0)
            self.pntrials['right_n'].set_height(right_n)
            self.pntrials['right_n'].set_y(right_p)
            self.pntrials['right_r'].set_height(right_r)
            self.pntrials['right_r'].set_y(right_n+right_p)
                           
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

        
        self.ppsych = {'block' : self.h['axpsych'].plot([],[],'.--',
                                                         clip_on = False,
                                                         color=colors[0])[0],
                       'total' : self.h['axpsych'].plot([],[],'.--',
                                                        clip_on = False,
                                                        color=colors[1])[0]}
        self.h['axpsych'].legend([self.ppsych['block'],
                                  self.ppsych['total']],
                                 ['blk','all'],fontsize='x-small',
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
 

