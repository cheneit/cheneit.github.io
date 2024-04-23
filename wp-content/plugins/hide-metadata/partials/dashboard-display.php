<?php

/**
 * Provide a admin area view for the plugin
 *
 * This file is used to markup the admin-facing aspects of the plugin.
 *
 * @link      https://catchplugins.com/plugins/hide-metadata
 * @since      1.0.0
 *
 * @package    Hide_Metadata
 * @subpackage Hide_Metadata/partials
 */
?>

<div id="hide-metadata">
	<div class="content-wrapper">
		<div class="header">
			<h2><?php esc_html_e( 'Settings', 'hide-metadata' ); ?></h2>
		</div> <!-- .Header -->
		<div class="content">
			<?php if ( isset( $_GET['settings-updated'] ) ) { ?>
			<div id="message" class="notice updated fade">
				<p><strong><?php esc_html_e( 'Plugin Options Saved.', 'hide-metadata' ); ?></strong></p>
			</div>
			<?php } ?>
			<?php
			// Use nonce for verification.
				wp_nonce_field( HIDE_METADATA_BASENAME, 'hide_metadata_nonce' );
			?>
			<div id="hide_metadata_main" class="hide-metadata-main">
				<form method="post" action="options.php">
					<?php settings_fields( 'hide-metadata-group' ); ?>
					<?php
					$settings = hide_metadata_get_options();
					?>
					<div class="option-container">
						<table class="form-table" bgcolor="white">
							<tbody>
								<tr>
									<th>
									<?php esc_html_e( 'Hide By', 'hide-metadata' ); ?>
									</th>
									<td>
										<select name="hide_metadata_options[hide_by]" id="hide_metadata_options[hide_by]">
										<option value="css" <?php echo selected( $settings['hide_by'], 'css', false ); ?> ><?php esc_html_e( 'CSS', 'hide-metadata' ); ?></option>
										<option value="php" <?php echo selected( $settings['hide_by'], 'php', false ); ?> ><?php esc_html_e( 'PHP', 'hide-metadata' ); ?></option>			
									</select>
									<span class="dashicons dashicons-info tooltip" title="<?php esc_html_e( 'Whether you want to hide it with CSS only or you remove it from the Page/Code.', 'hide-metadata' ); ?>"></span>
									</td>
								</tr>
								<tr>
									<th scope="row"><?php esc_html_e( 'Hide author', 'hide-metadata' ); ?></th>
									<td>
										<div class="module-header <?php echo $settings['hide_author'] ? 'active' : 'inactive'; ?>">
											<div class="switch">
												<input type="checkbox" id="hide_metadata_options[hide_author]" value="1" name="hide_metadata_options[hide_author]" class="shm-input-switch" rel="hide_author" <?php checked( 1, $settings['hide_author'] ); ?> >
												<label for="hide_metadata_options[hide_author]"></label>
											</div>
										</div>
									</td>
								</tr>
								<tr>
									<th scope="row"><?php esc_html_e( 'Hide published date', 'hide-metadata' ); ?></th>
									<td>
										<div class="module-header <?php echo $settings['hide_date'] ? 'active' : 'inactive'; ?>">
											<div class="switch">
												<input type="checkbox" id="hide_metadata_options[hide_date]" value="1" name="hide_metadata_options[hide_date]" class="shm-input-switch" rel="hide_date" <?php checked( 1, $settings['hide_date'] ); ?> >
												<label for="hide_metadata_options[hide_date]"></label>
											</div>
										</div>
									</td>
								</tr>
								<tr>
									<th scope="row"><?php esc_html_e( 'Reset Options', 'hide-metadata' ); ?></th>
									<td>
										<?php
											echo '<input name="hide_metadata_options[reset]" id="hide_metadata_options[reset]" type="checkbox" value="1" class="hide_metadata_options[reset]" />' . esc_html__( 'Check to reset', 'hide-metadata' );
										?>
										<span class="dashicons dashicons-info tooltip" title="<?php esc_html_e( 'Caution: Reset all settings to default.', 'hide-metadata' ); ?>"></span>
									</td>
								</tr>
							</tbody>
						</table>
						<?php submit_button( esc_html__( 'Save Changes', 'hide-metadata' ) ); ?>
					</div><!-- .option-container -->
				</form>
			</div><!-- sticky_main -->
		</div><!-- .content -->
	</div><!-- .content-wrapper -->
</div><!---hide-metadata-->
