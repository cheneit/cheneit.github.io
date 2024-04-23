<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the installation.
 * You don't have to use the web site, you can copy this file to "wp-config.php"
 * and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * Database settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://wordpress.org/documentation/article/editing-wp-config-php/
 *
 * @package WordPress
 */

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'xceias_com' );

/** Database username */
define( 'DB_USER', 'xceias_com' );

/** Database password */
define( 'DB_PASSWORD', 'bsJeahetTEYZzRJc' );

/** Database hostname */
define( 'DB_HOST', 'localhost' );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8mb4' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**#@+
 * Authentication unique keys and salts.
 *
 * Change these to different unique phrases! You can generate these using
 * the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}.
 *
 * You can change these at any point in time to invalidate all existing cookies.
 * This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY',         'A0SSa#MiMk[s!8VT>eOJr nSjZ/@7:,dFw];PBWfu}}j_`+&L%b}AC;ye`#0fy4`' );
define( 'SECURE_AUTH_KEY',  '>>>R^gJmB`uzrF]O(f=(v,w`/OocUW`#~!8KDXh`pbewOHa>b7:pwem$NH2!O2~u' );
define( 'LOGGED_IN_KEY',    '4@6#mLHRCraJC]Z}dy$JL@C3GM7J@A;r%YL6IOtdF{d.pS&@%KHol05r_32?8U8W' );
define( 'NONCE_KEY',        '=CuA&$y4C1lqWJ.#ytYy1W)@Jcx[;/o4(.cR-ADaO|z^Q;vn^y;4Spt5,-w3*R+F' );
define( 'AUTH_SALT',        '^HG_?VqlgHLtFEJauWTEz$RCQ=:#>edB*:dRma=DmlUW^*+28^G2 5<Twk}6KjmG' );
define( 'SECURE_AUTH_SALT', '#sBgX|c_Jut~ih9FHf e.UPCnJ27^pZ|?o=;Ie kRC !kNR):_}|H1c?aaKYaMSV' );
define( 'LOGGED_IN_SALT',   'u#W1hzq9LF]b Aj::C)dC4G:s?d$4a jkt3a{M!;:&AU7Ff*uIEsDR@Ko= ^Ac$T' );
define( 'NONCE_SALT',       'yZoJgyUzWnJR+&i:^q.wrMgIqGZ;fW?__:@@nHEBR xeaR*^EBa$)pQs@7jFYP@k' );

/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'wp_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the documentation.
 *
 * @link https://wordpress.org/documentation/article/debugging-in-wordpress/
 */
define( 'WP_DEBUG', false );

/* Add any custom values between this line and the "stop editing" line. */



/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
