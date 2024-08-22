    def process_screenshot(self, img, window_left, window_top):
        timestamp = time.time()
        print(f"\nTimestamp: {timestamp}")

        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        health_bars = [
            {"name": "Thirst", "position": (1087, 687)},
            {"name": "Hunger", "position": (1118, 683)},
            {"name": "Temperature", "position": (1149, 698)},
            {"name": "Blood", "position": (1185, 697)},
            {"name": "Health", "position": (1202, 687)},
        ]

        # BGR format
        white_lower = np.array([170, 170, 170])  
        white_upper = np.array([255, 255, 255])
        yellow_lower = np.array([0, 180, 180])
        yellow_upper = np.array([100, 255, 255])
        red_lower = np.array([0, 0, 150])
        red_upper = np.array([100, 100, 255])


        for bar in health_bars:
            x, y = bar["position"]
            color = img_cv[y, x]
            
            if np.all(color == [0, 0, 0]):
                state = "DEAD"
            elif np.all((color >= white_lower) & (color <= white_upper)):
                state = "White (Best)"
            elif np.all((color >= yellow_lower) & (color <= yellow_upper)):
                state = "Yellow (Okay)"
            elif np.all((color >= red_lower) & (color <= red_upper)):
                state = "Red (Critical)"
            else:
                state = "Unknown"
            
            print(f"{bar['name']} at ({x}, {y}): {state} (Color: {color})")
