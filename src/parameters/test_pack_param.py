import sys
from src.parameters.pack_param import pack_imu_calibration

def test():    
    def verify(packed):
        wx = (packed >> 20) & 0xF
        wy = (packed >> 24) & 0xF
        wz = (packed >> 28) & 0xF
        
        mask_x = (1 << wx) - 1
        mask_y = (1 << wy) - 1
        mask_z = (1 << wz) - 1
        
        raw_x = (packed >> 0) & mask_x
        raw_y = (packed >> wx) & mask_y
        raw_z = (packed >> (wx + wy)) & mask_z
        
        def sign_extend(val, w):
            if val & (1 << (w-1)): return val - (1 << w)
            return val
            
        return sign_extend(raw_x, wx), sign_extend(raw_y, wy), sign_extend(raw_z, wz)

    tests = [
        (2, 4, 5),       
        (-1, -2, -4),    
        (10, -15, 0),    
        (127, -128, 63)
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
            
    if passed == len(tests):
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(test())
