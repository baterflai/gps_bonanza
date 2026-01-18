import sys
from src.parameters.pack_param import pack_imu_calibration

def test():    
    def verify(packed):
        # Decode header pivots
        p2 = (packed >> 27) & 0x1F
        p1 = (packed >> 22) & 0x1F
        
        wx = p1
        wy = p2 - p1
        wz = 22 - p2
        
        mask_x = (1 << wx) - 1
        mask_y = (1 << wy) - 1
        mask_z = (1 << wz) - 1
        
        raw_x = (packed >> 0) & mask_x
        raw_y = (packed >> p1) & mask_y
        raw_z = (packed >> p2) & mask_z
            
        return raw_x, raw_y, raw_z

    tests = [
        (2, 4, 5),       
        (1, 2, 4),    
        (10, 15, 0),    
        (127, 128, 31)
    ]
    
    passed = 0
    for i, (x, y, z) in enumerate(tests):
        try:
            packed = pack_imu_calibration(x, y, z)
            if packed is None:
                print(f"Test {i+1}: FAIL. Returned None")
                continue
                
            rx, ry, rz = verify(packed)
            
            if (rx, ry, rz) == (x, y, z):
                print(f"Test {i+1}: PASS. Packed: {packed:#010x} -> Unpacked: {rx}, {ry}, {rz}")
                passed += 1
            else:
                print(f"Test {i+1}: FAIL. Input: {x,y,z}, Unpacked: {rx,ry,rz}")
        except Exception as e:
            print(f"Test {i+1}: ERROR {e}")
            import traceback
            traceback.print_exc()
            
    if passed == len(tests):
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(test())
