    def check_health_bars(self, img_cv):
        health_bars = [
            {"name": "Thirst", "position": (1087, 687)},
            {"name": "Hunger", "position": (1118, 683)},
            {"name": "Blood", "position": (1185, 697)},
            {"name": "Health", "position": (1202, 687)},
        ]

        white_lower, white_upper = np.array([170, 170, 170]), np.array([255, 255, 255])
        yellow_lower, yellow_upper = np.array([0, 180, 180]), np.array([100, 255, 255])
        red_lower, red_upper = np.array([0, 0, 150]), np.array([100, 100, 255])

        results = {}
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
            
            results[bar['name']] = state

        return results
