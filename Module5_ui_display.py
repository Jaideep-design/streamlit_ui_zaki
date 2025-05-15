# import tkinter as tk
# from tkinter import ttk

# class LiveDataUI:
#     def __init__(self, root, column_names):
#         self.root = root
#         self.root.title("Live Solar AC Data")
#         self.tree = ttk.Treeview(root, columns=column_names, show='headings')

#         for col in column_names:
#             self.tree.heading(col, text=col)
#             self.tree.column(col, width=100)

#         self.tree.pack(expand=True, fill='both')

#     def update_row(self, data_dict):
#         # Clear existing rows
#         for row in self.tree.get_children():
#             self.tree.delete(row)

#         # Insert new data
#         row = [data_dict.get(col, '') for col in self.tree["columns"]]
#         self.tree.insert('', 'end', values=row)

# def launch_ui(data_dict):
#     root = tk.Tk()
#     ui = LiveDataUI(root, list(data_dict.keys()))
#     ui.update_row(data_dict)
#     root.mainloop()

# In[]
import tkinter as tk

def launch_ui(column_names, get_latest_data_func):
    root = tk.Tk()
    root.title("Live Data Display")

    # Create labels for each column
    labels = {}
    for idx, col in enumerate(column_names):
        tk.Label(root, text=col, font=('Arial', 12, 'bold')).grid(row=0, column=idx, padx=10, pady=5)
        labels[col] = tk.Label(root, text="--", font=('Arial', 12))
        labels[col].grid(row=1, column=idx, padx=10, pady=5)

    def update_ui():
        data = get_latest_data_func()
        for col in column_names:
            value = data.get(col, "--")
            labels[col].config(text=str(value))
            print(f"UImodule:{col} ---> {value}  ")
        root.after(1000, update_ui)  # Schedule the next update in 1000 ms

    update_ui()  # Start the update loop
    root.mainloop()
