from typing import Tuple
import PySimpleGUI as sg
from selenium import webdriver

import time
from datetime import datetime
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from scipy import interpolate

import csv
import os

class Zetamac:
    def __init__(self, link: str, game_time: int) -> None:

        self.link = link
        self.game_time = game_time
        
        # check data.csv exists
        if not os.path.isfile('.\data.csv'):
            with open('.\data.csv', 'w') as f:
                writer = csv.writer(f)
                header = ['time','score']
                writer.writerow(header)
                f.close()
        
        self.driver = webdriver.Chrome('.\chromedriver')
        self.main()

    def main(self) -> None:
        """
        Control flow of program
        """

        self.init_browser()
        self.init_game()

    def init_game(self) -> None:
        """
        Called at the beginning of every game
        """

        time.sleep(self.game_time)
        score = self.store_data()
        self.end_of_game(score)

    def init_browser(self) -> None:
        """
        Initialise the browser
        """

        self.driver.get(self.link)
        self.driver.maximize_window()

    def store_data(self) -> int:
        """
        Attempt to store data
        """

        try:
            score = self.driver.find_element_by_xpath('//*[@id="game"]/div/div[2]/p[1]').text.split()[-1]

        except IndexError:
            print('Score not in! Trying again in 2 seconds.')
            time.sleep(3)
            score = self.driver.find_element_by_xpath('//*[@id="game"]/div/div[2]/p[1]').text.split()[-1]

        with open('.\data.csv', 'a', newline = '') as f:
            writer = csv.writer(f)
            data = [datetime.now(), score]
            writer.writerow(data)
            f.close()

        return score

    def end_of_game(self, score: int) -> None:
        """
        GUI for end of game scenario
        """

        sg.theme('DarkAmber')
        font = ('Roboto Mono', 10)

        layout = [
                    [sg.Text(size=(1,1), key='-OUT-')],
                    [sg.Text('Score: {}'.format(score), font = ('Roboto Mono', 16))],
                    [sg.Text('Restarting in ...', key = '-TEXT-')],
                    [sg.Text(size=(1,1), key='-OUT-')],
                    [sg.Button('Play Again'), sg.Button('Stats'), sg.Button('Exit')]
                ]

        window = sg.Window(
            'Zetamac', 
            layout,
            element_justification='c',
            size=(400, 175),
            font = font,
            finalize=True
        )

        timer = Countdown(5)

        window.bring_to_front()

        while True:
            # event loop
            event, values = window.read(timeout = 10)

            if event in (sg.WIN_CLOSED ,'Exit'):
                self.driver.quit()
                window.close()
                break

            elif event == 'Play Again' or not timer.status():
                window.close()
                self.restart_game()
                break

            elif event == 'Stats':
                window.close()
                self.stats(score)
                break

            window['-TEXT-'].update('Restarting in ... {}'.format(timer.counting()))

    def restart_game(self) -> None:
        """
        Restart the game
        """

        self.driver.find_element_by_xpath('//*[@id="game"]/div/div[2]/p[2]/a[1]').click()
        self.driver.find_element_by_xpath('//*[@id="game"]/div/div[1]/input').click()

        self.init_game()
    
    def stats(self, score: int) -> None:
        """
        GUI for performance statistics dashboard    
        """

        statistics = self.stats_calculation()
        self.generate_stat_plot()

        sg.theme('DarkAmber')
        font = ('Roboto Mono', 10)

        image = [[sg.Image('./plot.png')]]
        col = [
            [sg.Text('score',font = ('Roboto Mono', 14))],
            [sg.Text(score, font = ('Roboto Mono', 22), text_color= 'white')],
            [sg.Text(size=(1,1), key='-OUT-')],
            [sg.Text('pb',font = ('Roboto Mono', 14))],
            [sg.Text(statistics[0],font = ('Roboto Mono', 22), text_color= 'white')]
        ]

        def mini_col(label, score):
            return sg.Column([[sg.Text(label, font = ('Roboto Mono', 10))],[sg.Text(score, font = ('Roboto Mono', 16), text_color= 'white')]])

        layout = [
                    [sg.Column(col), 
                    sg.Column(image, element_justification='c')],
                    [
                        mini_col('best today', statistics[1]),
                        mini_col('av (last 10)',statistics[2]),
                        mini_col('std (last 10)',statistics[3]),
                        mini_col('time today',statistics[4]),
                        mini_col('av (all time)',statistics[5])
                        ],
                    [sg.Text(size = (1,1), key = '-OUT-')],
                    [sg.Button('Play Again'), sg.Button('Exit')]
                ]

        window = sg.Window(
            'Zetamac', 
            layout,
            element_justification='c',
            size=(1200, 650),
            font = font
        )
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Exit':
            window.close()
            self.driver.quit()

        if event == 'Play Again':
            window.close()
            self.restart_game()

    def stats_calculation(self) -> Tuple:
        """
        Output a tuple containg stats for dashboard in following format:
        (pb, best today, av (last 10), std dev (last 10), time today, av (all time))
        """

        data = pd.read_csv('./data.csv')
        data['time'] = pd.to_datetime(data['time'])

        today_results = data.loc[
            data['time'].dt.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d")]

        pb = str(int(data[['score']].max()))

        best_today = str(int(today_results['score'].max()))

        av_last_ten = '{:.1f}'.format(data.tail(10)['score'].mean())

        std_last_ten = '{:.1f}'.format(data.tail(10)['score'].std())

        time_today = '{}m'.format(len(today_results) * self.game_time / 60)

        av_all_time = '{:.1f}'.format(data['score'].mean())

        return (
            pb, best_today, av_last_ten, std_last_ten, time_today, av_all_time
            )
        
    def generate_stat_plot(self) -> None:
        """
        Generate or update plot for last ten scores
        """

        if os.path.isfile('.\plot.png'):
            os.remove('.\plot.png')

        data = pd.read_csv('./data.csv')

        x = [x for x in range(1,11)]
        if len(data) < 10:
            y = list(np.zeros(10 - len(data), dtype = int))
            y += list(data['score'])
        else:
            y = list(data.tail(10)['score'])

        x_new = np.linspace(1, 10, 300)
        a_BSpline = interpolate.make_interp_spline(x, y)
        y_new = a_BSpline(x_new)

        fig, ax = plt.subplots()
        plt.plot(x_new, y_new, color = '#fccb54')
        plt.plot(x, y, 'x', color = 'white')

        ax.xaxis.label.set_color('#fccb54')
        ax.yaxis.label.set_color('#fccb54')
        ax.tick_params(axis='y', colors='#fccb54')
        plt.xlabel('Last Ten Games')
        plt.ylabel('Score')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        plt.xticks([])
        ax.grid(axis='y')

        plt.savefig('plot.png', transparent=True)

class Countdown:
    def __init__(self, seconds: int):
        self.target_time = int(time.time()) + seconds
        self.running = True
    
    def counting(self):
        """
        Returns seconds until timer is complete
        """
        time_remaining = max(self.target_time - int(time.time()), 0)
        if not time_remaining:
            self.running = False

        return time_remaining

    def status(self):
        """
        Check if countdown has reached expiry 
        """
        return self.running

if __name__ == '__main__':
    Zetamac('https://arithmetic.zetamac.com/game?key=a7220a92', 120)