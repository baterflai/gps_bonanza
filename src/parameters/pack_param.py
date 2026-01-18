def pack_imu_calibration(x, y, z):
    """
    Encodes three integers (X, Y, Z) into a packed 32-bit IMU calibration parameter.

    Args:
        x, y, z: Integers to pack.
        
    Returns:
        int: The packed 32-bit unsigned integer.

    ------------------------------------------------------------

    Description:
    
    The 32-bit integer is split into a Header and Payload.
    
    Header (10 bits): Defines the pivots for the fields.
        [31:27] Pivot 2 (P2): End of Y / Start of Z
        [26:22] Pivot 1 (P1): End of X / Start of Y
    
    Payload (22 bits): Stores the values X, Y, Z sequentially.
        [21:0] Data
        
    Layout:
        X: [0 : P1]
        Y: [P1 : P2]
        Z: [P2 : 22]
    """
    # TODO
    
    return 0
