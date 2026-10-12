import Flutter
import Photos
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)

    if let controller = window?.rootViewController as? FlutterViewController {
      let channel = FlutterMethodChannel(
        name: "makeupart/gallery",
        binaryMessenger: controller.binaryMessenger
      )
      channel.setMethodCallHandler { call, result in
        guard call.method == "saveImage" else {
          result(FlutterMethodNotImplemented)
          return
        }
        guard
          let arguments = call.arguments as? [String: Any],
          let typedBytes = arguments["bytes"] as? FlutterStandardTypedData,
          let image = UIImage(data: typedBytes.data)
        else {
          result(FlutterError(
            code: "EMPTY_IMAGE",
            message: "Image data is missing or invalid.",
            details: nil
          ))
          return
        }

        PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
          guard status == .authorized else {
            DispatchQueue.main.async {
              result(FlutterError(
                code: "PHOTO_PERMISSION_DENIED",
                message: "Allow photo access to save this result to Photos.",
                details: nil
              ))
            }
            return
          }
          PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.creationRequestForAsset(from: image)
          }, completionHandler: { success, error in
            DispatchQueue.main.async {
              if success {
                result("photos-library")
              } else {
                result(FlutterError(
                  code: "GALLERY_SAVE_FAILED",
                  message: error?.localizedDescription ?? "Could not save image to Photos.",
                  details: nil
                ))
              }
            }
          })
        }
      }
    }
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
