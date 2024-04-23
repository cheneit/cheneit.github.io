<?php

/**
 * Provide a admin area view for the plugin
 *
 * This file is used to markup the admin-facing aspects of the plugin.
 *
 * @link       www.catchplugins.com
 * @since      1.0.0
 *
 * @package    Hide_Metadata
 * @subpackage Hide_Metadata/admin/partials
 */
?>

<!-- This file should primarily consist of HTML with a little bit of PHP. -->
<div class="wrap">
    <h1 class="wp-heading-inline"><?php esc_html_e( 'Hide/Remove Metadata', 'hide-metadata' );?></h1>
    <div id="plugin-description">
        <p><?php esc_html_e( 'Hide/Remove Metadata is a free, simple yet extremely handy WordPress plugin that helps you hide author and published date either by CSS or PHP from your website effortlessly.', 'hide-metadata' ); ?></p>
    </div>
    <div class="catchp-content-wrapper">
        <div class="catchp_widget_settings">
            <form id="sticky-main" method="post" action="options.php">
                <h2 class="nav-tab-wrapper">
                    <a class="nav-tab nav-tab-active" id="dashboard-tab" href="#dashboard"><?php esc_html_e( 'Dashboard', 'hide-metadata' ); ?></a>
                    <a class="nav-tab" id="features-tab" href="#features"><?php esc_html_e( 'Features', 'hide-metadata' ); ?></a>
                    
                </h2>
                <div id="dashboard" class="wpcatchtab nosave active">
                    <?php require_once plugin_dir_path( dirname( __FILE__ ) ) . 'partials/dashboard-display.php';?>
                   
                </div><!---dashboard---->

                <div id="features" class="wpcatchtab save">
                    <div class="content-wrapper col-3">
                        <div class="header">
                            <h3><?php esc_html_e( 'Features', 'hide-metadata' );?></h3>
                        </div><!-- .header -->
                        <div class="content">
                            <ul class="catchp-lists">
                               <li>
                                    <strong><?php esc_html_e( 'Hide or Remove Metadata', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'With Hide/Remove Metadata plugin, you have the freedom to either hide the author and published date or remove them completely. To partially hide the information, select CSS and to completely remove them, select PHP. By selecting and hiding through CSS, one can simply get the information with the Inspect tool. However, with PHP, the information would completely be removed, even the Inspect tool would not display the author or published date information.', 'hide-metadata' ); ?></p>
                                </li>
                                
                                <li>
                                    <strong><?php esc_html_e( 'Hide Author', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'If you want to hide the author of your blog, simply turn on the Hide Author option. It depends on the previous customization option if the author information would be just hidden or completely removed.', 'hide-metadata' ); ?></p>
                                </li>
                                <li>
                                    <strong><?php esc_html_e( 'Hide Published Date', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'Turn on the Hide Published Date option if you want to hide the published date of articles. This option is handy when it comes to evergreen articles, articles that are never outdated.', 'hide-metadata' ); ?></p>
                                </li>
                                <li>
                                    <strong><?php esc_html_e( 'Lightweight', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'Hide/Remove Metadata is an expedient WordPress plugin to hide or remove author and published date that is extremely lightweight. It means you will not have to worry about your website getting slower because of the plugin.', 'hide-metadata' ); ?></p>
                                </li>
                                <li>
                                    <strong><?php esc_html_e( 'Responsive Design', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'Our new plugin comes with a responsive design, therefore, there is no need to strain about the plugin breaking your website.', 'hide-metadata' ); ?></p>
                                </li>
                                <li>
                                    <strong><?php esc_html_e( 'Compatible with all WordPress Themes', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'Gutenberg Compatibility is one of the major concerns nowadays for every plugin developer. Our new Hide/Remove Metadata plugin has been crafted in a way that supports all the WordPress themes. The plugin functions smoothly on any WordPress theme.', 'hide-metadata' ); ?></p>
                                </li>
                                <li>
                                    <strong><?php esc_html_e( 'Incredible Support', 'hide-metadata' ); ?></strong>
                                    <p><?php esc_html_e( 'Hide/Remove Metadata comes with Incredible Support. Our plugin documentation answers most questions about using the plugin.  If you’re still having difficulties, you can post it in our Support Forum.', 'hide-metadata' ); ?></p>
                                </li>
                            </ul>
                                
                        </div><!-- .content -->
                    </div><!-- content-wrapper -->
                </div> <!-- Featured -->
            </form><!-- sticky-main -->
        </div><!-- .catchp_widget_settings -->
        <?php require_once plugin_dir_path(dirname(__FILE__) ) .'/partials/sidebar.php';?>
    </div><!---catch-content-wrapper---->
<?php require_once plugin_dir_path( dirname( __FILE__ ) ) . '/partials/footer.php'; ?>
</div><!-- .wrap -->

