import tkinter as tk
import random
import time

width = 600
height = 300
bar_width = 22
delay = 0.25  # Delay between visualization steps (seconds)

class Visualizer:
    def __init__(self,root):
        self.root = root
        self.root.title("Algorithm Visualizer")

        self.canvas = tk.Canvas(root, width=width, height=height, bg="purple") # Creates the Window
        self.canvas.pack() #Kind of initializes

        self.arr = [random.randint(10,100) for _ in range(20)] # Array of 20 random ints from 10 to 100
        self.draw_bars() # Initial draw of Bars

        tk.Button(root, text="Bubble Sort", command=self.bubble_sort).pack(side=tk.LEFT)
        tk.Button(root, text="Selection Sort", command=self.selection_sort).pack(side=tk.LEFT)
        tk.Button(root, text="Linear Search", command=lambda: self.linear_search(50)).pack(side=tk.LEFT) # Right now 50 pre_defined will make dynamic input later..

    def draw_bars(self, highlight=None): # THE MAIN DRAWING SUB-ROUTINE
        self.canvas.delete("all") # Clear previous bars (Kind of like refreash)
        for i,val in enumerate(self.arr):
            x0 = i*bar_width
            y0 = height-(val*2)
            x1 = x0+bar_width
            y1 = height

            color = "red" if highlight and i in highlight else "Yellow" # Color coded, update later on..
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=color)
        self.root.update() # Force canvas update
        time.sleep(delay) # Refresh Delay

    #    ALGORITHMS
    def bubble_sort(self):
        n=len(self.arr)
        for i in range(n):
            for j in range(n-i-1):
                self.draw_bars(highlight=(j, j+1)) # Highlight the selected 2 Elements
                if self.arr[j] > self.arr[j+1]:
                    self.arr[j], self.arr[j+1] = self.arr[j+1], self.arr[j] # swap
                    self.draw_bars(highlight=(j, j+1))
                    
    def selection_sort(self):
        n=len(self.arr)
        for i in range(n):
            min_idx = i
            for j in range(i+1,n):
                self.draw_bars(highlight=(min_idx, j))
                if self.arr[j] < self.arr[min_idx]:
                    min_idx = j
            self.arr[i], self.arr[min_idx] = self.arr[min_idx], self.arr[i]
            self.draw_bars(highlight=(i, min_idx))

    def linear_search(self, target):
        for i in range(len(self.arr)):
            self.draw_bars(highlight=(i, ))
            if self.arr[i] == target:
                self.canvas.delete("all")
                for j,val in enumerate(self.arr):
                    x0 = j*bar_width
                    y0 = height-(val*2)
                    x1 = x0+bar_width
                    y1 = height
                    if j == i:
                        color = "green"  # Found
                    else:
                        color = "Yellow"
                    self.canvas.create_rectangle(x0,y0,x1,y1,fill=color)
                self.root.update()
                return  # Stop searching once found for better efficiency

#Main Program
root = tk.Tk()
app = Visualizer(root)
root.mainloop()