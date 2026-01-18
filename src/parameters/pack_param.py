def pack_imu_calibration(x, y, z):
    """
    Encodes three signed integers (X, Y, Z) into a packed 32-bit IMU calibration parameter.

    Args:
        x, y, z (int): Integers to pack.
        
    Returns:
        int: The packed 32-bit unsigned integer.

    ------------------------------------------------------------

    Description:
    
    The 32-bit integer is split into a Header and Payload.
    
    Header: Defines the bit-width of each value:
        [31:28] Width of Z (4 bits)
        [27:24] Width of Y (4 bits)
        [23:20] Width of X (4 bits)
    
    Payload stores the values Z, Y, X sequentially.
    
    Layout: [...padding...][Z][Y][X]
    """
    # TODO: Implement this function using only bitwise operators and if/else
    # <<, >>, &, |, ^, ~
    
    return 0
