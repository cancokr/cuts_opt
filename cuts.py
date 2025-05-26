import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# --- 파라미터 입력용 GUI 함수 ---
def get_parameters():
    root = tk.Tk()
    root.title("파라미터 입력")
    fields = [
        ("원판 가로 (mm)", "1500"),
        ("원판 세로 (mm)", "1200"),
        ("원판 Offset (mm)", "2"),
        ("조각 가로 (mm)", "200"),
        ("조각 세로 (mm)", "150"),
        ("조각 Offset (mm)", "1")
    ]
    entries = {}
    for i, (label, default) in enumerate(fields):
        tk.Label(root, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
        entry = tk.Entry(root)
        entry.insert(0, default)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries[label] = entry
    def submit():
        params = {}
        try:
            for label, entry in entries.items():
                params[label] = float(entry.get())
            root.params = params
            root.destroy()
        except ValueError:
            tk.messagebox.showerror("입력 오류", "숫자를 확인하세요.")
    tk.Button(root, text="확인", command=submit).grid(row=len(fields), column=0, columnspan=2, pady=10)
    root.mainloop()
    return getattr(root, "params", None)

def calculate_layout_in_area(area_w, area_h, piece_w, piece_h, gap):
    """
    주어진 영역에 특정 크기의 조각을 배치하고 개수, 위치, 사용된 너비/높이를 반환합니다.
    조각은 행 우선으로 배치됩니다 (가로로 먼저 채우고 다음 줄).
    """
    if piece_w <= 0 or piece_h <= 0:
        return 0, [], 0, 0
    if piece_w > area_w or piece_h > area_h:
        return 0, [], 0, 0

    # 첫 조각은 왼쪽에 gap이 필요 없음
    num_cols = 0
    if area_w >= piece_w:
        num_cols = 1 + math.floor((area_w - piece_w) / (piece_w + gap))

    # 첫 조각은 위쪽에 gap이 필요 없음
    num_rows = 0
    if area_h >= piece_h:
        num_rows = 1 + math.floor((area_h - piece_h) / (piece_h + gap))
    
    count = num_cols * num_rows
    positions = []
    actual_width_used = 0
    actual_height_used = 0

    if count > 0:
        for r_idx in range(num_rows):
            for c_idx in range(num_cols):
                x = c_idx * (piece_w + gap)
                y = r_idx * (piece_h + gap)
                positions.append({'x': x, 'y': y, 'w': piece_w, 'h': piece_h, 'rotated': piece_w != piece_w_orig}) # 원본과 다르면 회전됨
        
        actual_width_used = num_cols * piece_w + (num_cols - 1) * gap if num_cols > 0 else 0
        actual_height_used = num_rows * piece_h + (num_rows - 1) * gap if num_rows > 0 else 0
            
    return count, positions, actual_width_used, actual_height_used

def find_optimal_layout_for_remainder(area_w, area_h, p_w_orig, p_h_orig, gap):
    """잉여 영역에 최적으로 조각을 배치하는 함수"""
    best_count = 0
    best_positions = []
    best_piece_dims = None

    orientations = [{'w': p_w_orig, 'h': p_h_orig, 'name': "Original"}]
    if p_w_orig != p_h_orig:
        orientations.append({'w': p_h_orig, 'h': p_w_orig, 'name': "Rotated"})

    for piece_opt in orientations:
        pw, ph = piece_opt['w'], piece_opt['h']
        count, pos_list, _, _ = calculate_layout_in_area(area_w, area_h, pw, ph, gap)
        if count > best_count:
            best_count = count
            best_positions = pos_list
            best_piece_dims = piece_opt
    
    return best_count, best_positions, best_piece_dims


def solve_cutting_problem(usable_w, usable_h, p_w_orig, p_h_orig, p_gap):
    """
    주어진 사용 가능 영역에 대해 최적의 배치 조합을 찾습니다.
    주 배치 후 남는 잉여 영역(오른쪽, 아래)에도 배치를 시도합니다.
    """
    global piece_w_orig # 시각화를 위해 전역 변수 사용 (회전 여부 판단)
    piece_w_orig = p_w_orig

    best_total_pieces = 0
    best_final_positions = []
    best_config_description = ""

    # 시도할 주 배치 방향
    main_orientations = [{'w': p_w_orig, 'h': p_h_orig, 'name': "Original"}]
    if p_w_orig != p_h_orig: # 정사각형이 아니면 회전된 것도 시도
        main_orientations.append({'w': p_h_orig, 'h': p_w_orig, 'name': "Rotated"})

    for main_opt in main_orientations:
        main_piece_w, main_piece_h = main_opt['w'], main_opt['h']
        current_config_pieces = 0
        current_config_positions = []
        current_description_parts = []

        # 1. 주 영역 채우기
        main_count, main_pos, main_w_used, main_h_used = calculate_layout_in_area(
            usable_w, usable_h, main_piece_w, main_piece_h, p_gap
        )
        current_config_pieces += main_count
        current_config_positions.extend(main_pos)
        current_description_parts.append(f"Main {main_opt['name']}({main_count})")
        
        # 2. 잉여 영역1: 주 영역의 오른쪽
        rem1_x_offset = 0
        if main_w_used > 0 : rem1_x_offset = main_w_used + p_gap
        
        rem1_w = usable_w - rem1_x_offset
        rem1_h = usable_h # 오른쪽 남은 영역은 전체 높이 사용 가능

        if rem1_w > 0 and rem1_h > 0:
            rem1_count, rem1_pos_list, rem1_dims = find_optimal_layout_for_remainder(
                rem1_w, rem1_h, p_w_orig, p_h_orig, p_gap
            )
            if rem1_count > 0:
                current_config_pieces += rem1_count
                for p in rem1_pos_list:
                    current_config_positions.append({
                        'x': p['x'] + rem1_x_offset, 'y': p['y'], 
                        'w': p['w'], 'h': p['h'], 'rotated': p['w'] != p_w_orig
                    })
                current_description_parts.append(f"Right Remain {rem1_dims['name']}({rem1_count})")

        # 3. 잉여 영역2: 주 영역의 아래쪽 (주 영역이 사용한 너비만큼만)
        rem2_y_offset = 0
        if main_h_used > 0 : rem2_y_offset = main_h_used + p_gap

        rem2_w = main_w_used # 주 영역이 사용한 너비만큼
        rem2_h = usable_h - rem2_y_offset

        if rem2_w > 0 and rem2_h > 0:
            rem2_count, rem2_pos_list, rem2_dims = find_optimal_layout_for_remainder(
                rem2_w, rem2_h, p_w_orig, p_h_orig, p_gap
            )
            if rem2_count > 0:
                current_config_pieces += rem2_count
                for p in rem2_pos_list:
                    current_config_positions.append({
                        'x': p['x'], 'y': p['y'] + rem2_y_offset,
                        'w': p['w'], 'h': p['h'], 'rotated': p['w'] != p_w_orig
                    })
                current_description_parts.append(f"Bottom Remain {rem2_dims['name']}({rem2_count})")
        
        # 현재 설정이 더 좋으면 업데이트
        if current_config_pieces > best_total_pieces:
            best_total_pieces = current_config_pieces
            best_final_positions = current_config_positions
            best_config_description = " | ".join(current_description_parts)

    return best_total_pieces, best_final_positions, best_config_description


def plot_layout(sheet_w, sheet_h, sheet_offset, usable_w, usable_h, pieces, title=""):
    import matplotlib.font_manager as fm
    # font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    try:
        font_prop = fm.FontProperties(fname=font_path)
    except:
        font_prop = None

    fig, ax = plt.subplots(1, figsize=(10, 10 * sheet_h / sheet_w if sheet_w > 0 else 10))
    ax.set_aspect('equal', adjustable='box')

    # 1. 전체 원판
    ax.add_patch(patches.Rectangle((0, 0), sheet_w, sheet_h, facecolor='lightgray', edgecolor='black'))
    
    # 2. 사용 불가 영역 (offset)
    # 상단 offset
    ax.add_patch(patches.Rectangle((0, sheet_h - sheet_offset), sheet_w, sheet_offset, facecolor='dimgray', alpha=0.7))
    # 하단 offset
    ax.add_patch(patches.Rectangle((0, 0), sheet_w, sheet_offset, facecolor='dimgray', alpha=0.7))
    # 좌측 offset
    ax.add_patch(patches.Rectangle((0, sheet_offset), sheet_offset, sheet_h - 2 * sheet_offset, facecolor='dimgray', alpha=0.7))
    # 우측 offset
    ax.add_patch(patches.Rectangle((sheet_w - sheet_offset, sheet_offset), sheet_offset, sheet_h - 2 * sheet_offset, facecolor='dimgray', alpha=0.7))

    # 3. 사용 가능 영역 (흰색으로 덮어씌워 명확히)
    ax.add_patch(patches.Rectangle((sheet_offset, sheet_offset), usable_w, usable_h, facecolor='white', edgecolor='green', linewidth=1.5))

    # 4. 배치된 조각들
    for i, piece in enumerate(pieces):
        # 조각 위치는 사용 가능 영역의 (0,0) 기준이므로, sheet_offset을 더해줌
        rect_x = piece['x'] + sheet_offset
        rect_y = piece['y'] + sheet_offset
        
        color = 'deepskyblue' if not piece.get('rotated', False) else 'lightcoral' # 회전 여부에 따라 색상 변경
        
        ax.add_patch(patches.Rectangle((rect_x, rect_y), piece['w'], piece['h'], facecolor=color, edgecolor='black'))
        # ax.text(rect_x + piece['w']/2, rect_y + piece['h']/2, str(i+1), ha='center', va='center', fontsize=8)


    ax.set_xlim(0, sheet_w)
    ax.set_ylim(0, sheet_h)
    ax.set_title(title)
    

    plt.gca().invert_yaxis() # (0,0)을 좌상단으로
    ax.set_xlabel("Width (mm)", fontproperties=font_prop)
    ax.set_ylabel("Height (mm)", fontproperties=font_prop)
    plt.tight_layout()
    plt.show()

def plot_layout_ax(ax, sheet_w, sheet_h, sheet_offset, usable_w, usable_h, pieces, title=""):
    ax.set_aspect('equal', adjustable='box')
    ax.add_patch(patches.Rectangle((0, 0), sheet_w, sheet_h,
                                  facecolor='lightgray', edgecolor='black'))
    # unusable offsets
    ax.add_patch(patches.Rectangle((0, sheet_h - sheet_offset), sheet_w, sheet_offset,
                                  facecolor='dimgray', alpha=0.7))
    ax.add_patch(patches.Rectangle((0, 0), sheet_w, sheet_offset, facecolor='dimgray', alpha=0.7))
    ax.add_patch(patches.Rectangle((0, sheet_offset), sheet_offset, sheet_h - 2 * sheet_offset,
                                  facecolor='dimgray', alpha=0.7))
    ax.add_patch(patches.Rectangle((sheet_w - sheet_offset, sheet_offset), sheet_offset,
                                  sheet_h - 2 * sheet_offset, facecolor='dimgray', alpha=0.7))
    # usable area
    ax.add_patch(patches.Rectangle((sheet_offset, sheet_offset), usable_w, usable_h,
                                  facecolor='white', edgecolor='green', linewidth=1.5))
    # pieces
    for piece in pieces:
        x = piece['x'] + sheet_offset
        y = piece['y'] + sheet_offset
        color = 'deepskyblue' if not piece.get('rotated', False) else 'lightcoral'
        ax.add_patch(patches.Rectangle((x, y), piece['w'], piece['h'],
                                      facecolor=color, edgecolor='black'))
    ax.set_xlim(0, sheet_w)
    ax.set_ylim(sheet_h, 0)  # invert y
    ax.set_title(title)

# --- 전역 변수 (조각 원본 크기, 회전 여부 판단용) ---
piece_w_orig = 0 


def launch_app():
    # Create main window
    root = tk.Tk()
    root.title("Cutting Layout Optimizer")

    # Divide into input and output frames
    input_frame = tk.Frame(root)
    input_frame.pack(side='left', fill='y', padx=10, pady=10)
    plot_frame = tk.Frame(root)
    plot_frame.pack(side='right', fill='both', expand=True)

    # Define fields
    params = {
        "Sheet Width (mm)": tk.DoubleVar(value=1500),
        "Sheet Height (mm)": tk.DoubleVar(value=1200),
        "Sheet Offset (mm)": tk.DoubleVar(value=3),
        "Piece Width (mm)": tk.DoubleVar(value=200),
        "Piece Height (mm)": tk.DoubleVar(value=150),
        "Piece Gap (mm)": tk.DoubleVar(value=5),
        "3D Curve": tk.BooleanVar(value=False),
        "Radius (mm)": tk.DoubleVar(value=1000),
    }
    entries = {}
    radius_entry = None
    # Create input widgets, but skip "3D Curve" for now (will add Checkbutton), and handle Radius specially
    row_idx = 0
    for label, var in params.items():
        if label == "3D Curve":
            continue
        if label == "Radius (mm)":
            # Will add after 3D Curve checkbox
            continue
        tk.Label(input_frame, text=label).grid(row=row_idx, column=0, sticky='e')
        entry = tk.Entry(input_frame, textvariable=var)
        entry.grid(row=row_idx, column=1, pady=2)
        entries[label] = var
        row_idx += 1
    # Add 3D Curve checkbutton above Radius input
    is3d_var = params["3D Curve"]
    cb = tk.Checkbutton(input_frame, text="3D Curve", variable=is3d_var)
    cb.grid(row=row_idx, column=0, columnspan=2, pady=2)
    row_idx += 1
    # Now add Radius input
    tk.Label(input_frame, text="Radius (mm)").grid(row=row_idx, column=0, sticky='e')
    radius_entry = tk.Entry(input_frame, textvariable=params["Radius (mm)"])
    radius_entry.grid(row=row_idx, column=1, pady=2)
    # Disable radius entry initially
    radius_entry.config(state='disabled')
    # Add callback to enable/disable radius entry when 3D Curve is checked
    def toggle_radius():
        radius_entry.config(state='normal' if is3d_var.get() else 'disabled')
    cb.config(command=toggle_radius)
    row_idx += 1
    # Create Update button
    update_btn = tk.Button(input_frame, text="Update", command=lambda: update_plot())
    update_btn.grid(row=row_idx, column=0, columnspan=2, pady=10)

    # Create matplotlib Figure and Canvas
    fig = Figure(figsize=(8,6))
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.get_tk_widget().pack(fill='both', expand=True)

    # Plot update function
    def update_plot():
        # Read values
        sw = params["Sheet Width (mm)"].get()
        sh = params["Sheet Height (mm)"].get()
        so = params["Sheet Offset (mm)"].get()
        pw = params["Piece Width (mm)"].get()
        ph = params["Piece Height (mm)"].get()
        gap = params["Piece Gap (mm)"].get()
        is3d = params["3D Curve"].get()
        radius = params["Radius (mm)"].get()

        # Compute flat_pw if 3D curve is on
        if is3d and radius > 0 and pw <= 2 * radius:
            flat_pw = radius * 2 * math.asin(pw / (2 * radius))
        else:
            flat_pw = pw

        usable_w = sw - 2*so
        usable_h = sh - 2*so
        # Compute hybrid solution
        total_pieces, final_positions, _ = solve_cutting_problem(usable_w, usable_h, flat_pw, ph, gap)
        # Compute horizontal-only
        hc, hpos, _, _ = calculate_layout_in_area(usable_w, usable_h, flat_pw, ph, gap)
        for p in hpos: p['x']+=so; p['y']+=so; p['rotated']=False
        # Compute vertical-only
        vc, vpos, _, _ = calculate_layout_in_area(usable_w, usable_h, ph, flat_pw, gap)
        for p in vpos: p['x']+=so; p['y']+=so; p['rotated']=True

        scenarios = [
            ("Horizontal Only", hc, hpos),
            ("Vertical Only", vc, vpos),
            ("Hybrid", total_pieces, final_positions)
        ]
        # sort
        sc_sorted = sorted(scenarios, key=lambda x: x[1], reverse=True)
        piece_area = flat_pw * ph
        eff_map = {name: (cnt * piece_area / (usable_w*usable_h) * 100) if usable_w*usable_h>0 else 0
                   for name, cnt, _ in scenarios}

        # Clear figure
        fig.clf()
        import matplotlib.gridspec as gridspec
        gs = gridspec.GridSpec(2, 2, figure=fig, width_ratios=[2,1], height_ratios=[1,1], wspace=0.3, hspace=0.3)

        # annotate piece size or curve/flat
        if is3d:
            fig.text(0.01, 0.98, f"Curve width: {pw} mm, Flat length: {flat_pw:.1f} mm  Height: {ph} mm", va='top', ha='left', fontsize=10)
        else:
            fig.text(0.01, 0.98, f"Piece size: {pw} x {ph} mm", va='top', ha='left', fontsize=10)

        # best
        ax0 = fig.add_subplot(gs[:,0])
        n0, c0, p0 = sc_sorted[0]
        title0 = f"{n0}: {c0} pcs, {eff_map[n0]:.1f}%"
        plot_layout_ax(ax0, sw, sh, so, usable_w, usable_h, p0, title=title0)

        # second
        ax1 = fig.add_subplot(gs[0,1])
        n1, c1, p1 = sc_sorted[1]
        title1 = f"{n1}: {c1} pcs, {eff_map[n1]:.1f}%"
        plot_layout_ax(ax1, sw, sh, so, usable_w, usable_h, p1, title=title1)

        # third
        ax2 = fig.add_subplot(gs[1,1])
        n2, c2, p2 = sc_sorted[2]
        title2 = f"{n2}: {c2} pcs, {eff_map[n2]:.1f}%"
        plot_layout_ax(ax2, sw, sh, so, usable_w, usable_h, p2, title=title2)

        canvas.draw()

    # Initial plot
    update_plot()

    root.mainloop()

if __name__ == "__main__":
    launch_app()